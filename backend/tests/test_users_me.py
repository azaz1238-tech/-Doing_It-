"""내 정보 조회 API 테스트 (T-F1-03, AUTH-04, API-SPEC §1.2·§5.1·§10 인증).

완료 기준: 토큰 없음 401, 비활성 403. 토큰 형식·서명·만료 검사는 test_core.py에서 한다.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from core.config import get_settings
from core.security import JWT_ALGORITHM, create_access_token
from tests.factories import make_project, make_task, make_user

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


# --- 내 이름 수정 (T-F1-06, AUTH-06, API-SPEC §6 PATCH /users/me · §5.1 이름 규칙) ---


def test_update_me_200_changes_name(client, db):
    user = make_user(db, name="지수")
    headers = _auth(create_access_token(user.id))

    res = client.patch(URL, headers=headers, json={"name": "민지"})

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"id", "login_id", "name", "system_role", "created_at"}
    assert body["id"] == user.id
    assert body["name"] == "민지"
    # 저장됐는지: 다시 조회해도 바뀐 이름
    assert client.get(URL, headers=headers).json()["name"] == "민지"


def test_update_me_strips_whitespace(client, db):
    user = make_user(db, name="지수")

    res = client.patch(
        URL, headers=_auth(create_access_token(user.id)), json={"name": "  민지  "}
    )

    assert res.status_code == 200
    assert res.json()["name"] == "민지"


def test_update_me_50_chars_ok(client, db):
    """경계: 한글 50자는 통과 (바이트가 아니라 글자 수)"""
    user = make_user(db)

    res = client.patch(
        URL, headers=_auth(create_access_token(user.id)), json={"name": "가" * 50}
    )

    assert res.status_code == 200
    assert res.json()["name"] == "가" * 50


@pytest.mark.parametrize(
    "name",
    ["가" * 51, "", "   ", None],
    ids=["51자", "빈 값", "공백만", "null"],
)
def test_update_me_invalid_name_422(client, db, name):
    """51자·빈 값·공백만·null → 422, 이름은 그대로 (TASKS T-F1-06 완료 기준, AUTH-06-b)"""
    user = make_user(db, name="지수")
    headers = _auth(create_access_token(user.id))

    res = client.patch(URL, headers=headers, json={"name": name})

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "name"
    assert client.get(URL, headers=headers).json()["name"] == "지수"


def test_update_me_empty_object_422(client, db):
    """빈 객체 {} → name이 빠짐 → 422 (field = name)"""
    user = make_user(db)

    res = client.patch(URL, headers=_auth(create_access_token(user.id)), json={})

    assert res.status_code == 422
    assert res.json()["errors"][0]["field"] == "name"


def test_update_me_extra_field_422(client, db):
    """이름 말고 다른 필드(login_id 등)는 받지 않는다 → 아무것도 바뀌지 않음"""
    user = make_user(db, login_id="jisoo01", name="지수")
    headers = _auth(create_access_token(user.id))

    res = client.patch(
        URL, headers=headers, json={"name": "민지", "login_id": "hacker1"}
    )

    assert res.status_code == 422
    me = client.get(URL, headers=headers).json()
    assert me["login_id"] == "jisoo01"
    assert me["name"] == "지수"


def test_update_me_without_token_401(client):
    res = client.patch(URL, json={"name": "민지"})
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_update_me_disabled_user_403(client, db):
    user = make_user(db, is_active=False)

    res = client.patch(
        URL, headers=_auth(create_access_token(user.id)), json={"name": "민지"}
    )

    assert res.status_code == 403
    assert res.json()["code"] == "ACCOUNT_DISABLED"


def test_update_me_shows_in_task_and_comment(client, db):
    """AUTH-06-a: 이름을 바꾸면 업무 담당자·댓글 작성자 표시에 바뀐 이름이 보인다"""
    user = make_user(db, name="지수")
    project = make_project(db, user)
    task = make_task(db, project, user, assignee_id=user.id)
    headers = _auth(create_access_token(user.id))
    created = client.post(
        f"/api/tasks/{task.id}/comments", headers=headers, json={"content": "확인"}
    )
    assert created.status_code == 201

    assert client.patch(URL, headers=headers, json={"name": "민지"}).status_code == 200

    detail = client.get(f"/api/tasks/{task.id}", headers=headers).json()
    assert detail["assignee"]["name"] == "민지"
    assert detail["created_by"]["name"] == "민지"
    comments = client.get(f"/api/tasks/{task.id}/comments", headers=headers).json()
    assert comments["items"][0]["user"]["name"] == "민지"
