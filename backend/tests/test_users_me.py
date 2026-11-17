"""내 정보 조회 API 테스트 (T-F1-03, AUTH-04, API-SPEC §1.2·§5.1·§10 인증).

완료 기준: 토큰 없음 401, 비활성 403. 토큰 형식·서명·만료 검사는 test_core.py에서 한다.
"""

from datetime import UTC, datetime, timedelta

import jwt

from core.config import get_settings
from core.security import JWT_ALGORITHM, create_access_token
from tests.factories import make_user

URL = "/api/users/me"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_me_200_returns_user_without_password_hash(client, db):
    user = make_user(db, login_id="jisoo01", name="지수")

    res = client.get(URL, headers=_auth(create_access_token(user.id)))

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"id", "login_id", "name", "system_role", "created_at"}
    assert body["id"] == user.id
    assert body["login_id"] == "jisoo01"
    assert body["name"] == "지수"


def test_login_token_works_for_me(client, db):
    """로그인으로 받은 토큰으로 내 정보를 조회한다 (새로고침 복원 흐름)."""
    make_user(db, login_id="jisoo01")
    login = client.post(
        "/api/auth/login", json={"login_id": "jisoo01", "password": "password123"}
    )

    res = client.get(URL, headers=_auth(login.json()["access_token"]))

    assert res.status_code == 200
    assert res.json()["login_id"] == "jisoo01"


def test_me_without_token_401(client):
    res = client.get(URL)
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"
    assert res.headers["WWW-Authenticate"] == "Bearer"


def test_me_expired_token_401(client, db):
    user = make_user(db)
    expired = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        get_settings().jwt_secret_key,
        algorithm=JWT_ALGORITHM,
    )
    assert client.get(URL, headers=_auth(expired)).status_code == 401


def test_me_unknown_user_401(client):
    """서명은 맞지만 사용자가 없는 토큰 → 401"""
    res = client.get(URL, headers=_auth(create_access_token(999_999)))
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_me_disabled_user_403(client, db):
    user = make_user(db, is_active=False)

    res = client.get(URL, headers=_auth(create_access_token(user.id)))

    assert res.status_code == 403
    assert res.json() == {
        "code": "ACCOUNT_DISABLED",
        "message": "사용할 수 없는 계정입니다",
    }
