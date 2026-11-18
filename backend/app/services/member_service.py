"""멤버 서비스 (ARCHITECTURE §4.4, API-SPEC §5.3).

멤버 추가(PRJ-04)·제거(PRJ-05)도 이 파일에 둔다.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ProjectMember, User
from app.schemas.member import MemberOut
from app.services.permissions import ANY_MEMBER, owner_first, require_project_role


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
