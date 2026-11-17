"""로그인 API 테스트 (T-F1-02, AUTH-02, API-SPEC §5.1·§10 인증).

완료 기준: 틀린 비밀번호 401. SPEC AUTH-02-a(성공)·b(틀린 정보)·c(비활성 계정).
"""

import pytest

from core.security import decode_access_token
from tests.factories import DEFAULT_PASSWORD, make_user

URL = "/api/auth/login"
INVALID = {
    "code": "INVALID_CREDENTIALS",
    "message": "아이디 또는 비밀번호가 올바르지 않습니다",
}


def _login(client, login_id="jisoo01", password=DEFAULT_PASSWORD):
    return client.post(URL, json={"login_id": login_id, "password": password})


def test_login_200_returns_token_for_user(client, db):  # AUTH-02-a
    user = make_user(db, login_id="jisoo01")

    res = _login(client)

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 7200
    assert decode_access_token(body["access_token"]) == user.id


def test_login_id_stripped_and_lowercased(client, db):
    make_user(db, login_id="jisoo01")
    assert _login(client, login_id="  JiSoo01 ").status_code == 200


@pytest.mark.parametrize(
    ("login_id", "password"),
    [
        ("jisoo01", "wrongpass123"),  # 틀린 비밀번호 (AUTH-02-b)
        ("nobody99", DEFAULT_PASSWORD),  # 없는 아이디
        ("ab", DEFAULT_PASSWORD),  # 형식이 틀린 아이디 → 422 아님
        ("jisoo01", f" {DEFAULT_PASSWORD} "),  # 비밀번호 공백은 지우지 않는다
        ("jisoo01", "가" * 25),  # 72바이트 초과 → 422 아님
    ],
)
def test_invalid_credentials_401(client, db, login_id, password):
    make_user(db, login_id="jisoo01")

    res = _login(client, login_id=login_id, password=password)

    assert res.status_code == 401
    assert res.json() == INVALID


def test_disabled_account_403_only_with_right_password(client, db):  # AUTH-02-c
    make_user(db, login_id="jisoo01", is_active=False)

    wrong = _login(client, password="wrongpass123")
    right = _login(client)

    assert wrong.status_code == 401  # 비밀번호가 틀리면 비활성 여부를 알려 주지 않는다
    assert right.status_code == 403
    assert right.json()["code"] == "ACCOUNT_DISABLED"


@pytest.mark.parametrize(
    "body",
    [
        {"login_id": "jisoo01"},  # 필드 없음
        {"login_id": 1234, "password": DEFAULT_PASSWORD},  # 문자열 아님
    ],
)
def test_malformed_body_422(client, body):
    res = client.post(URL, json=body)
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"
