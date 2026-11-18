"""멤버 응답 스키마 (API-SPEC §4 Member, §5.3)."""

from pydantic import BaseModel

from app.models.enums import ProjectRole
from app.schemas.common import UtcDatetime


class MemberOut(BaseModel):
    """Member 객체. user_id는 users.id (project_members.id가 아님)."""

    user_id: int
    login_id: str
    name: str
    role: ProjectRole
    joined_at: UtcDatetime
