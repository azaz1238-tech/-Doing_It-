"""회원가입 API 테스트 (T-F1-01, AUTH-01·03). 완료 기준: 중복 409, 73바이트 한글 422."""

import pytest
from sqlalchemy import select

from app.models import User
from core.security import verify_password
from tests.factories import make_user

URL = "/api/auth/signup"
VALID = {"login_id": "jisoo01", "password": "password123", "name": "지수"}
LOGIN_ID_MESSAGE = "영문 소문자·숫자 4~20자로 입력해 주세요."


def _signup(client, **overrides):
    return client.post(URL, json={**VALID, **overrides})


def _field_errors(res) -> dict:
    return {e["field"]: e["message"] for e in res.json()["errors"]}


def test_signup_201_without_token(client):
    res = _signup(client)
    assert res.status_code == 201
    body = res.json()
    assert set(body) == {"id", "login_id", "name", "system_role", "created_at"}
    assert body["login_id"] == "jisoo01"
    assert body["name"] == "지수"
    assert body["system_role"] == "USER"
    assert body["created_at"].endswith("Z")


def test_login_id_lowercased_and_name_stripped(client):
    res = _signup(client, login_id="  JiSoo01 ", name="  지수  ")
    assert res.status_code == 201
    assert res.json()["login_id"] == "jisoo01"
    assert res.json()["name"] == "지수"


def test_password_stored_as_bcrypt_hash(client, db):  # AUTH-03
    _signup(client)
    user = db.scalars(select(User).where(User.login_id == "jisoo01")).one()
    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash)


@pytest.mark.parametrize("login_id", ["jisoo01", "JISOO01"])
def test_duplicate_login_id_409(client, db, login_id):
    make_user(db, login_id="jisoo01")
    res = _signup(client, login_id=login_id)
    assert res.status_code == 409
    assert res.json() == {
        "code": "LOGIN_ID_ALREADY_EXISTS",
        "message": "이미 사용 중인 아이디입니다.",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("login_id", "abc", LOGIN_ID_MESSAGE),
        ("login_id", "a" * 21, LOGIN_ID_MESSAGE),
        ("login_id", "ji_soo", LOGIN_ID_MESSAGE),
        ("login_id", "지수아이디", LOGIN_ID_MESSAGE),
        ("password", "a" * 7, "8자 이상 입력해 주세요."),
        ("password", "a" * 65, "64자 이하로 입력해 주세요."),
        # 완료 기준: 25자(64자 이하)지만 75바이트 → 422
        ("password", "가" * 25, "72바이트 이하로 입력해 주세요 (한글은 24자까지)."),
        ("name", "   ", "1자 이상 입력해 주세요."),
        ("name", "가" * 51, "50자 이하로 입력해 주세요."),
    ],
)
def test_signup_validation_422(client, field, value, message):
    res = _signup(client, **{field: value})
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"
    assert _field_errors(res) == {field: message}


def test_password_exactly_72_bytes_ok(client):
    assert _signup(client, password="가" * 24).status_code == 201


def test_extra_or_missing_field_422(client):
    res = client.post(URL, json={**VALID, "system_role": "ADMIN"})
    assert res.status_code == 422
    assert _field_errors(res) == {"system_role": "정의되지 않은 필드입니다."}
    res = client.post(URL, json={"login_id": "jisoo01"})
    assert set(_field_errors(res)) == {"password", "name"}
