"""프로젝트 권한 검사 공통 함수 (ARCHITECTURE §4.4, API-SPEC §1.5).

- 역할 비교는 이 파일에서만 한다. 서비스·라우터에서 member.role == ... 처럼 직접 비교하지 않는다(CLAUDE.md §5).
- 프로젝트 하위 리소스(업무·댓글·이력)도 먼저 이 함수로 멤버인지 확인한다(CONSTITUTION 6-4).
- 업무 API는 업무를 먼저 조회(없으면 404 TASK_NOT_FOUND)한 뒤 task.project_id로 이 함수를 부른다.
"""

from sqlalchemy import ColumnElement, case, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, Task, User
from app.models.enums import ProjectRole
from core.exceptions import BusinessRuleError, Forbidden, NotFound

# 자주 쓰는 허용 역할 묶음
ANY_MEMBER: frozenset[ProjectRole] = frozenset(ProjectRole)
OWNER_ONLY: frozenset[ProjectRole] = frozenset({ProjectRole.OWNER})


def require_project_role(
    db: Session,
    project_id: int,
    user: User,
    allowed: frozenset[ProjectRole] | set[ProjectRole],
) -> ProjectMember:
    """프로젝트 존재 → 멤버 여부 → 역할 순서로 검사하고, 통과하면 내 멤버십을 돌려준다.

    - 프로젝트 없음 → 404 PROJECT_NOT_FOUND
    - 멤버 아님     → 403 NOT_PROJECT_MEMBER
    - 역할 불일치   → 403 FORBIDDEN
    """
    if db.get(Project, project_id) is None:
        raise NotFound("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다")

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    if member is None:
        raise Forbidden("NOT_PROJECT_MEMBER", "프로젝트 멤버가 아닙니다")

    if ProjectRole(member.role) not in allowed:
        raise Forbidden("FORBIDDEN", "권한이 없습니다")

    return member


def owner_first() -> ColumnElement[int]:
    """멤버 목록 정렬용 식: OWNER면 0, 아니면 1 (PRJ-07, DATABASE-DESIGN §8.2).

    역할 값 비교라서 이 파일에 둔다. 서비스는 order_by(owner_first(), ...)로만 쓴다.
    """
    return case((ProjectMember.role == ProjectRole.OWNER.value, 0), else_=1)


def lock_owners(db: Session, project_id: int) -> list[ProjectMember]:
    """이 프로젝트의 OWNER 행을 모두 잠그고 돌려준다 (DATABASE-DESIGN §6.1).

    OWNER 수를 세기 전에 부른다. 두 OWNER가 동시에 서로를 제거하면
    두 번째 요청은 첫 번째가 끝날 때까지 기다린 뒤 줄어든 OWNER 수를 본다.
    역할 변경(PRJ-08)·나가기(PRJ-09)·탈퇴(AUTH-08)도 OWNER 수를 바꾸므로 반드시 이 함수를 쓴다.

    참고: REPEATABLE READ에서 잠그며 읽으면 훑은 인덱스 범위가 함께 잠겨,
    실제로는 이 프로젝트의 멤버 행 대부분이 잠긴다. 트랜잭션이 짧아 문제는 없다.
    """
    return list(
        db.scalars(
            select(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectRole.OWNER.value,
            )
            .order_by(ProjectMember.id)  # 잠그는 순서를 고정해 교착 상태를 막는다
            .with_for_update()
        )
    )


def require_not_last_owner(owners: list[ProjectMember], target: ProjectMember) -> None:
    """대상이 마지막 OWNER면 400 LAST_OWNER. owners는 lock_owners()의 결과."""
    if ProjectRole(target.role) in OWNER_ONLY and len(owners) <= 1:
        raise BusinessRuleError("LAST_OWNER", "OWNER는 최소 1명 있어야 합니다")


# ---------- 업무 권한 (TASK-06 권한 매트릭스, API-SPEC §5.4) — 서승범 추가 ----------
# require_project_role로 멤버 확인을 마친 뒤 부른다. 업무 작성자 판정도 여기서 한다.

# 담당자(작성자 아님)가 바꿀 수 있는 필드
_ASSIGNEE_EDITABLE: frozenset[str] = frozenset({"status"})


def _is_owner_or_author(member: ProjectMember, task: Task) -> bool:
    return ProjectRole(member.role) in OWNER_ONLY or task.created_by == member.user_id


def require_task_edit(member: ProjectMember, task: Task, fields: set[str]) -> None:
    """업무 수정 권한. fields는 요청에 보낸 필드 이름들.

    - OWNER 또는 작성자 → 전부
    - 담당자(작성자 아님) → status만. 다른 필드가 하나라도 있으면 요청 전체 403
    - 그 외 MEMBER → 403 FORBIDDEN
    """
    if _is_owner_or_author(member, task):
        return
    if task.assignee_id == member.user_id and fields <= _ASSIGNEE_EDITABLE:
        return
    raise Forbidden("FORBIDDEN", "권한이 없습니다")


def require_task_delete(member: ProjectMember, task: Task) -> None:
    """업무 삭제 권한: OWNER 또는 작성자만. 담당자·그 외 MEMBER는 403 FORBIDDEN."""
    if not _is_owner_or_author(member, task):
        raise Forbidden("FORBIDDEN", "권한이 없습니다")
