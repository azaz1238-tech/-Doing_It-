"""비밀번호 해시와 JWT (ARCHITECTURE §4.1, API-SPEC §1.2).

- 비밀번호는 bcrypt로만 저장한다 (passlib는 쓰지 않는다).
- JWT는 HS256, 담는 값은 sub(사용자 id 문자열)·exp뿐이다.
- 스타터킷 파일이므로 app/를 import하지 않는다.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from core.config import get_settings

JWT_ALGORITHM = "HS256"
# bcrypt는 72바이트를 넘는 비밀번호를 처리하지 못한다 (회원가입 스키마에서 422로 막는다)
PASSWORD_MAX_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호가 해시와 맞는지 확인한다. 72바이트 초과·깨진 해시는 예외 대신 False."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """토큰이 유효하면 사용자 id, 서명 오류·만료·형식 오류면 None."""
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
