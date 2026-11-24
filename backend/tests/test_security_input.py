"""DB·입력값 보안 회귀 테스트 (D10-03).

공격·경계 입력을 넣어도 500이 나지 않고, 정해진 4xx나 글자 그대로의 저장·검색이 되는지 고정한다.
결과서: docs/reports/2026-11-24-security-db-input.md. 인증·권한(양준석), XSS·토큰 노출(최진영)은 범위 밖.
"""

import pytest
from sqlalchemy import func, select

from app.models import Task, User
from core.security import create_access_token
from tests.factories import make_project, make_task, make_user

HUGE_IDS = [str(2**63), str(10**30), "9" * 4301, "-1", "0"]
HUGE_ID_NAMES = ["2^63", "10^30", "4301자리", "-1", "0"]


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def owner_project(db):
    owner = make_user(db)
    project = make_project(db, owner)
    return owner, project


# --- 1. 아주 큰 경로 id (Review Focus 1) ---


@pytest.mark.parametrize("big", HUGE_IDS, ids=HUGE_ID_NAMES)
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/projects/{id}"),
        ("GET", "/api/projects/{id}/tasks"),
        ("GET", "/api/tasks/{id}"),
        ("PATCH", "/api/comments/{id}"),
        ("DELETE", "/api/projects/{pid}/members/{id}"),
    ],
    ids=["project", "project-tasks", "task", "comment", "member"],
)
def test_huge_path_id_not_500(client, owner_project, method, path, big):
    owner, project = owner_project
    url = path.format(id=big, pid=project.id)
    body = {"content": "c"} if method == "PATCH" else None

    res = client.request(method, url, headers=_auth(owner), json=body)

    assert res.status_code in (403, 404, 422), res.text
    assert "code" in res.json()


# --- 2. 본문·쿼리의 아주 큰 정수 (Review Focus 5) ---


@pytest.mark.parametrize("big", [2**63, 10**30], ids=["2^63", "10^30"])
def test_huge_assignee_id_in_body_not_500(client, owner_project, big):
    owner, project = owner_project

    res = client.post(
        f"/api/projects/{project.id}/tasks",
        headers=_auth(owner),
        json={"title": "업무", "assignee_id": big},
    )

    assert res.status_code in (400, 422), res.text


# page 위쪽 한도가 없어 OFFSET이 MariaDB 정수 범위를 넘으면 SQL 오류 → 500 (core/pagination.py, A조).
# 목록 API 7개 공통, page ≥ 10^18부터. 고치면 XPASS가 실패로 보이므로 그때 이 표시를 지운다.
_PAGE_OVERFLOW = pytest.mark.xfail(
    strict=True,
    reason="D10-03: page 상한 없음 → OFFSET 범위 초과 500 (양준석 확인 요청)",
)


@pytest.mark.parametrize(
    ("param", "value"),
    [
        pytest.param("page", str(10**30), marks=_PAGE_OVERFLOW, id="page-10^30"),
        pytest.param("page", str(10**18), marks=_PAGE_OVERFLOW, id="page-10^18"),
        ("page", "-1"),
        ("page", "0"),
        ("page", "abc"),
        ("size", str(10**30)),
        ("size", "-1"),
        ("size", "0"),
        ("size", "abc"),
    ],
)
def test_page_size_out_of_range_422(client, owner_project, param, value):
    owner, project = owner_project

    res = client.get(
        f"/api/projects/{project.id}/tasks",
        headers=_auth(owner),
        params={param: value},
    )

    assert res.status_code == 422, res.text
    assert res.json()["errors"][0]["field"] == param


# --- 3. SQL·LIKE 문자열은 글자 그대로 (Review Focus 3) ---


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("' OR 1=1 --", []),
        ("%", ["50%_할인"]),
        ("_", ["50%_할인"]),
        ("50%_", ["50%_할인"]),
        ("\\", []),
    ],
    ids=["sql", "percent", "underscore", "both", "backslash"],
)
def test_search_q_sql_and_wildcards_literal(client, db, owner_project, q, expected):
    owner, project = owner_project
    make_task(db, project, owner, title="50%_할인")
    make_task(db, project, owner, title="일반")

    res = client.get(
        f"/api/projects/{project.id}/tasks", headers=_auth(owner), params={"q": q}
    )

    assert res.status_code == 200
    assert [t["title"] for t in res.json()["items"]] == expected


def test_sql_like_title_stored_literally(client, db, owner_project):
    owner, project = owner_project
    title = "'; DROP TABLE tasks; --"

    res = client.post(
        f"/api/projects/{project.id}/tasks",
        headers=_auth(owner),
        json={"title": title},
    )

    assert res.status_code == 201
    got = client.get(f"/api/tasks/{res.json()['id']}", headers=_auth(owner)).json()
    assert got["title"] == title
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Task)) == 1


# --- 4. 널 바이트·4바이트 이모지 (Review Focus 2) ---


@pytest.mark.parametrize(
    "text",
    ["a\x00b", "😀" * 30, "한글😀\U0001f9d1‍\U0001f4bb"],
    ids=["null-byte", "emoji-30", "zwj"],
)
def test_null_byte_and_emoji_round_trip(client, owner_project, text):
    """저장되면 보낸 값 그대로 돌아오고, 거절되면 422 — 어느 쪽이든 500·글자 깨짐은 없다."""
    owner, project = owner_project
    headers = _auth(owner)

    task = client.post(
        f"/api/projects/{project.id}/tasks", headers=headers, json={"title": text}
    )
    assert task.status_code in (201, 422), task.text
    if task.status_code == 201:
        assert task.json()["title"] == text
        tid = task.json()["id"]
        comment = client.post(
            f"/api/tasks/{tid}/comments", headers=headers, json={"content": text}
        )
        assert comment.status_code in (201, 422), comment.text
        if comment.status_code == 201:
            listed = client.get(f"/api/tasks/{tid}/comments", headers=headers).json()
            assert listed["items"][0]["content"] == text

    me = client.patch("/api/users/me", headers=headers, json={"name": text})
    assert me.status_code in (200, 422), me.text
    if me.status_code == 200:
        assert client.get("/api/users/me", headers=headers).json()["name"] == text


# --- 5. 정의되지 않은 필드 끼워 넣기 (Review Focus 4) ---


def test_signup_system_role_rejected(client, db):
    res = client.post(
        "/api/auth/signup",
        json={
            "login_id": "hacker1",
            "password": "password123",
            "name": "해커",
            "system_role": "ADMIN",
        },
    )

    assert res.status_code == 422
    assert db.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize(
    "extra",
    [{"created_by": 1}, {"project_id": 1}, {"id": 1}, {"completed_at": None}],
    ids=["created_by", "project_id", "id", "completed_at"],
)
def test_task_create_extra_field_rejected(client, db, owner_project, extra):
    owner, project = owner_project

    res = client.post(
        f"/api/projects/{project.id}/tasks",
        headers=_auth(owner),
        json={"title": "업무", **extra},
    )

    assert res.status_code == 422
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Task)) == 0


def test_project_update_my_role_rejected(client, owner_project):
    owner, project = owner_project

    res = client.patch(
        f"/api/projects/{project.id}", headers=_auth(owner), json={"my_role": "OWNER"}
    )

    assert res.status_code == 422


def test_comment_user_id_rejected(client, db, owner_project):
    owner, project = owner_project
    other = make_user(db)
    task = make_task(db, project, owner)

    res = client.post(
        f"/api/tasks/{task.id}/comments",
        headers=_auth(owner),
        json={"content": "남의 이름으로", "user_id": other.id},
    )

    assert res.status_code == 422


# --- 6. JSON이 아닌 본문·틀린 타입 ---


@pytest.mark.parametrize(
    "raw",
    ['{"title": ', "[]", '{"title": {"a": 1}}', '{"title": 123}', '"title"'],
    ids=["broken", "array", "object", "number", "string"],
)
def test_non_json_and_wrong_types_422(client, owner_project, raw):
    owner, project = owner_project

    res = client.post(
        f"/api/projects/{project.id}/tasks",
        headers={**_auth(owner), "Content-Type": "application/json"},
        content=raw,
    )

    assert res.status_code == 422, res.text
    assert res.json()["code"] == "VALIDATION_ERROR"
