"""프로젝트 권한 검사 공통 함수 (ARCHITECTURE §4.4, API-SPEC §1.5).

- 역할 비교는 이 파일에서만 한다. 서비스·라우터에서 member.role == ... 처럼 직접 비교하지 않는다(CLAUDE.md §5).
- 프로젝트 하위 리소스(업무·댓글·이력)도 먼저 이 함수로 멤버인지 확인한다(CONSTITUTION 6-4).
- 업무 API는 업무를 먼저 조회(없으면 404 TASK_NOT_FOUND)한 뒤 task.project_id로 이 함수를 부른다.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, User
from app.models.enums import ProjectRole
from core.exceptions import Forbidden, NotFound

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
