"""멤버 서비스 (ARCHITECTURE §4.4, API-SPEC §5.3).

멤버 추가(PRJ-04)·제거(PRJ-05)도 이 파일에 둔다.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ProjectMember, User
from app.schemas.member import MemberAdd, MemberOut
from app.services.permissions import (
    ANY_MEMBER,
    OWNER_ONLY,
    owner_first,
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
