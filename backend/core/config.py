"""환경 설정 — .env를 읽어 설정 객체 1개로 만든다 (ARCHITECTURE §4.1·§6).

스타터킷 파일이므로 app/를 import하지 않는다.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv

# JWT 서명 키 최소 길이 (ARCHITECTURE §6)
MIN_JWT_SECRET_LENGTH = 32


class ConfigError(RuntimeError):
    """필수 설정이 없거나 잘못되어 서버를 시작할 수 없을 때."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    test_database_url: str | None
    jwt_secret_key: str
    access_token_expire_minutes: int
    frontend_origin: str


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f".env에 {name} 값을 넣어 주세요 (docs/SETUP.md 1번).")
    return value


@lru_cache
def get_settings() -> Settings:
    """설정을 한 번만 읽어 재사용한다. 잘못된 값이면 ConfigError로 시작을 멈춘다."""
    # 이미 설정된 환경 변수가 .env보다 우선한다 (테스트에서 덮어쓰기 위함)
    load_dotenv(find_dotenv(), override=False)

    jwt_secret_key = _require("JWT_SECRET_KEY")
    if len(jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
        # 키 값 자체는 메시지에 넣지 않는다
        raise ConfigError(
            f"JWT_SECRET_KEY는 {MIN_JWT_SECRET_LENGTH}자 이상이어야 합니다 (docs/SETUP.md 1번)."
        )

    expire_raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120").strip()
    try:
        access_token_expire_minutes = int(expire_raw)
    except ValueError as exc:
        raise ConfigError("ACCESS_TOKEN_EXPIRE_MINUTES는 숫자여야 합니다.") from exc
    if access_token_expire_minutes <= 0:
        raise ConfigError("ACCESS_TOKEN_EXPIRE_MINUTES는 1 이상이어야 합니다.")

    return Settings(
        database_url=_require("DATABASE_URL"),
        test_database_url=os.getenv("TEST_DATABASE_URL", "").strip() or None,
        jwt_secret_key=jwt_secret_key,
        access_token_expire_minutes=access_token_expire_minutes,
        frontend_origin=_require("FRONTEND_ORIGIN").rstrip("/"),
    )
