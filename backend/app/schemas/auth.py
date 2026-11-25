"""인증 요청·응답 스키마 (API-SPEC §5.1, REQUIREMENTS AUTH-01).

입력 정리(공백 제거·소문자 변환)와 검증은 여기서 한다(ARCHITECTURE §4.2).
UserName은 내 이름 수정(AUTH-06)에서도 쓴다. Password는 비밀번호 변경(AUTH-07, P2 미구현)에서 다시 쓸 수 있다.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import SystemRole
from app.schemas.common import UtcDatetime
from core.security import PASSWORD_MAX_BYTES

_LOGIN_ID_PATTERN = re.compile(r"^[a-z0-9]{4,20}$")


def _check_login_id(value: str) -> str:
    if not _LOGIN_ID_PATTERN.fullmatch(value):
        raise ValueError("영문 소문자·숫자 4~20자로 입력해 주세요")
    return value


def _check_password_bytes(value: str) -> str:
    # bcrypt는 72바이트를 넘는 값을 처리하지 못한다. 한글은 1자 = 3바이트 → 24자까지
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError("72바이트 이하로 입력해 주세요 (한글은 24자까지)")
    return value


# 앞뒤 공백을 지우고 소문자로 바꾼 뒤 형식 검사 → 'MinHo'와 'minho'는 같은 아이디(409)
LoginId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True),
    AfterValidator(_check_login_id),
]
# 비밀번호는 공백을 지우지 않는다 (사용자가 넣은 그대로 해시)
Password = Annotated[
    str, Field(min_length=8, max_length=64), AfterValidator(_check_password_bytes)
]
UserName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_id: LoginId
    password: Password
    name: UserName


# 로그인 아이디는 정리만 하고 형식은 검사하지 않는다 → 형식이 틀려도 없는 아이디와 같은 401 (API-SPEC §5.1)
LoginIdInput = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True)]


class LoginRequest(BaseModel):
    """로그인 요청. 비밀번호는 길이·바이트 검사도, 공백 제거도 하지 않는다."""

    model_config = ConfigDict(extra="forbid")

    login_id: LoginIdInput
    password: str


class UpdateMeRequest(BaseModel):
    """내 이름 수정 (AUTH-06, API-SPEC §6). 이름 규칙은 회원가입과 같다(§5.1).
    이름 말고 다른 필드(login_id·system_role 등)는 받지 않는다 → 422."""

    model_config = ConfigDict(extra="forbid")

    name: UserName


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 초


class UserOut(BaseModel):
    """User 객체 (API-SPEC §4). password_hash·is_active는 필드 자체를 두지 않는다."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login_id: str
    name: str
    system_role: SystemRole
    created_at: UtcDatetime
