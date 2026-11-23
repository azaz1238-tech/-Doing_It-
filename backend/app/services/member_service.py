"""멤버 서비스 (ARCHITECTURE §4.4, API-SPEC §5.3).

멤버 추가(PRJ-04)·제거(PRJ-05)도 이 파일에 둔다.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ProjectMember, Task, User
from app.models.enums import ActivityAction, ActivityField
from app.schemas.member import MemberAdd, MemberOut
from app.services import activity_service
from app.services.permissions import (
    ANY_MEMBER,
    OWNER_ONLY,
    lock_owners,
    lock_project_shared,
    owner_first,
    require_not_last_owner,
    require_project_role,
)
from core.exceptions import Conflict, NotFound

# MariaDB 중복 키 오류 번호. auth_service에도 있다 — 세 번째로 쓰게 되면 core로 모은다.
_ER_DUP_ENTRY = 1062


def list_members(
    db: Session, user: User, project_id: int, offset: int, limit: int
) -> tuple[list[MemberOut], int]:
    """멤버 목록 (PRJ-07). 멤버만 볼 수 있다. 없음 404, 비멤버 403 NOT_PROJECT_MEMBER.

    정렬: OWNER 먼저 → joined_at → id (DATABASE-DESIGN §8.2).
    joined_at이 같은 초여도 순서가 흔들리지 않게 id로 한 번 더 정렬한다.
    """
    require_project_role(db, project_id, user, ANY_MEMBER)

    total = db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id)
    )
    rows = db.execute(
        select(
            User.id,
            User.login_id,
            User.name,
            ProjectMember.role,
            ProjectMember.joined_at,
        )
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(owner_first(), ProjectMember.joined_at, ProjectMember.id)
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        MemberOut(
            user_id=user_id,
            login_id=login_id,
            name=name,
            role=role,
            joined_at=joined_at,
        )
        for user_id, login_id, name, role, joined_at in rows
    ]
    return items, total


def add_member(db: Session, user: User, project_id: int, data: MemberAdd) -> MemberOut:
    """멤버 추가 (PRJ-04). OWNER만. 없는(또는 비활성) 아이디 404, 이미 멤버 409.

    아이디 조회는 권한 검사 뒤에 한다(API-SPEC §5.3) — 비멤버·MEMBER가 이 API로
    가입된 아이디를 알아내지 못하게 하기 위해서다.
    """
    require_project_role(db, project_id, user, OWNER_ONLY)

    target = db.scalar(select(User).where(User.login_id == data.login_id))
    # 비활성 계정도 같은 404로 답해 계정 상태를 드러내지 않는다
    if target is None or not target.is_active:
        raise NotFound("USER_NOT_FOUND", "해당 아이디의 회원이 없습니다")

    member = ProjectMember(project_id=project_id, user_id=target.id, role=data.role)
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # 미리 SELECT하지 않고 UNIQUE(project_id, user_id)에 맡긴다 → 동시에 추가해도 1건만 성공
        if exc.orig.args[0] == _ER_DUP_ENTRY:
            raise Conflict("ALREADY_MEMBER", "이미 프로젝트 멤버입니다") from exc
        raise
    db.refresh(member)  # DB가 넣은 joined_at을 읽는다

    return MemberOut(
        user_id=target.id,
        login_id=target.login_id,
        name=target.name,
        role=member.role,
        joined_at=member.joined_at,
    )


def remove_member(
    db: Session, user: User, project_id: int, target_user_id: int
) -> None:
    """멤버 제거 (PRJ-05). OWNER만(OWNER 자신 포함). 한 트랜잭션, 커밋 1번.

    P0에서는 MEMBER의 호출을 모두 403으로 막는다(본인 나가기는 P2 PRJ-09).
    """
    require_project_role(db, project_id, user, OWNER_ONLY)
    _remove_member_rows(db, project_id, target_user_id, actor_id=user.id)
    db.commit()


def _remove_member_rows(
    db: Session, project_id: int, target_user_id: int, actor_id: int
) -> None:
    """멤버 1명을 제거하는 DB 작업. 커밋하지 않는다 (ARCHITECTURE §4.3).

    1. OWNER 행 잠금 → 대상이 마지막 OWNER면 400
    2. 대상이 담당하던 업무의 담당자를 NULL로, 업무마다 이력 1행 (변경자 = actor)
    3. project_members 행 삭제

    잠그는 순서: 프로젝트 행(공유) → OWNER 행 → 대상 멤버 행 → 대상의 업무 행. 업무 담당자 지정은
    대상 멤버 행에 공유 잠금을 걸어(task_service._require_assignee_member) 이 순서와 맞춘다.
    프로젝트 행을 먼저 잠그는 것은 프로젝트 삭제와의 교착을 막기 위해서다(이슈 #72).
    여러 프로젝트에서 반복해 부를 때(AUTH-08 탈퇴)는 project_id 오름차순으로 부른다.
    """
    if not lock_project_shared(db, project_id):
        # 권한 검사 뒤에 다른 요청이 프로젝트를 삭제함
        raise NotFound("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다")
    owners = lock_owners(db, project_id)

    # 일반 SELECT는 트랜잭션 시작 시점의 값을 보여 줘서, 방금 다른 요청이 지운 행이
    # 보일 수 있다. 잠금과 함께 읽어(FOR UPDATE) 최신 값을 본다.
    target = db.scalar(
        select(ProjectMember)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
        .with_for_update()
    )
    if target is None:
        raise NotFound(
            "MEMBER_NOT_FOUND", "해당 사용자는 이 프로젝트의 멤버가 아닙니다"
        )
    require_not_last_owner(owners, target)

    tasks = db.scalars(
        select(Task)
        .where(Task.project_id == project_id, Task.assignee_id == target_user_id)
        .order_by(Task.id)
        .with_for_update()
    ).all()
    for task in tasks:
        activity_service.record(
            db,
            task,
            actor_id,
            ActivityAction.UPDATED,
            ActivityField.ASSIGNEE_ID,
            old_value=target_user_id,
            new_value=None,
        )
        task.assignee_id = None

    db.delete(target)
