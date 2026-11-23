"""멤버 응답 스키마 (API-SPEC §4 Member, §5.3)."""

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProjectRole
from app.schemas.auth import LoginIdInput
from app.schemas.common import UtcDatetime


class MemberOut(BaseModel):
    """Member 객체. user_id는 users.id (project_members.id가 아님)."""

    user_id: int
    login_id: str
    name: str
    role: ProjectRole
    joined_at: UtcDatetime


class MemberAdd(BaseModel):
    """멤버 추가 요청 (PRJ-04).

    login_id는 공백 제거·소문자 변환만 하고 형식은 검사하지 않는다(로그인과 같은 LoginIdInput).
    형식이 틀린 아이디는 가입된 아이디가 아니므로 404 USER_NOT_FOUND로 끝난다.
    """

    model_config = ConfigDict(extra="forbid")

    login_id: LoginIdInput
    role: ProjectRole


class MemberRoleUpdate(BaseModel):
    """역할 변경 요청 (PRJ-08). OWNER | MEMBER 외의 값·다른 필드는 422."""

    model_config = ConfigDict(extra="forbid")

    role: ProjectRole
