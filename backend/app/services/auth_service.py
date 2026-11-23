"""인증 도메인 서비스 (ARCHITECTURE §4.1·§4.4).

- signup: 회원가입 (T-F1-01)
- login: 로그인 (T-F1-02)
- get_current_user: 인증 필요 API의 공통 의존성 (T-F1-03)
- update_my_name: 내 이름 수정 (T-F1-06)
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenOut
from core.auth import get_token_user_id
from core.config import get_settings
from core.db import get_db
from core.exceptions import Conflict, Forbidden, Unauthorized
from core.security import create_access_token, hash_password, verify_password

# MariaDB 오류 번호: UNIQUE 위반
_ER_DUP_ENTRY = 1062

# 없는 아이디일 때도 bcrypt 비교를 한 번 해서, 응답 시간으로 계정 존재를 알 수 없게 한다
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


def signup(db: Session, data: SignupRequest) -> User:
    user = User(
        login_id=data.login_id,
        password_hash=hash_password(data.password),
        name=data.name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # 미리 SELECT로 확인하지 않고 UNIQUE에 맡긴다 → 동시에 가입해도 한 명만 성공
        if exc.orig.args[0] == _ER_DUP_ENTRY:
            raise Conflict(
                "LOGIN_ID_ALREADY_EXISTS", "이미 사용 중인 아이디입니다"
            ) from exc
        raise
    return user


def login(db: Session, data: LoginRequest) -> TokenOut:
    """검사 순서: 아이디 없음 401 → (탈퇴 401, P2) → 비밀번호 틀림 401 → 비활성 403 (API-SPEC §5.1)."""
    user = db.scalar(select(User).where(User.login_id == data.login_id))

    if user is None:
        verify_password(data.password, _DUMMY_PASSWORD_HASH)
        raise _invalid_credentials()
    # TODO(AUTH-08, P2): 탈퇴 계정(deleted_at)도 여기서 401 — 비활성 검사보다 먼저
    if not verify_password(data.password, user.password_hash):
        raise _invalid_credentials()
    if not user.is_active:
        raise _account_disabled()

    expires_in = get_settings().access_token_expire_minutes * 60
    return TokenOut(access_token=create_access_token(user.id), expires_in=expires_in)


def get_current_user(
    user_id: Annotated[int, Depends(get_token_user_id)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """토큰의 사용자를 조회한다. 없음 → 401 UNAUTHORIZED, 비활성 → 403 ACCOUNT_DISABLED (API-SPEC §1.2)."""
    user = db.get(User, user_id)
    # TODO(AUTH-08, P2): 탈퇴 계정(deleted_at)도 401
    if user is None:
        raise Unauthorized()
    if not user.is_active:
        raise _account_disabled()
    return user


def update_my_name(db: Session, user: User, name: str) -> User:
    """내 이름 수정 (T-F1-06). 업무·댓글 응답은 users를 조회해 이름을 넣으므로 바로 반영된다."""
    user.name = name
    db.commit()
    db.refresh(user)
    return user


def _invalid_credentials() -> Unauthorized:
    return Unauthorized(
        "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다"
    )


def _account_disabled() -> Forbidden:
    return Forbidden("ACCOUNT_DISABLED", "사용할 수 없는 계정입니다")
