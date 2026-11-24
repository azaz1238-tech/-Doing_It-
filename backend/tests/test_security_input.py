"""DB·입력값 보안 회귀 테스트 (D10-03).

공격·경계 입력을 넣어도 500이 나지 않고, 정해진 4xx나 글자 그대로의 저장·검색이 되는지 고정한다.
결과서: docs/reports/2026-11-24-security-db-input.md. 인증·권한(양준석), XSS·토큰 노출(최진영)은 범위 밖.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from app.models import Project, Task, TaskComment, User
from core.security import create_access_token
from tests.factories import make_project, make_task, make_user

# 4301자리는 정수 변환 단계에서 422, 나머지는 정수로 받아 DB에서 못 찾으므로 404
HUGE_IDS = [
    (str(2**63), 404),
    (str(10**30), 404),
    ("9" * 4301, 422),
    ("-1", 404),
    ("0", 404),
]
HUGE_ID_NAMES = ["2^63", "10^30", "4301자리", "-1", "0"]


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def owner_project(db):
    owner = make_user(db)
    project = make_project(db, owner)
    return owner, project


# --- 1. 아주 큰 경로 id (Review Focus 1) ---


@pytest.mark.parametrize(("big", "expected"), HUGE_IDS, ids=HUGE_ID_NAMES)
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
def test_huge_path_id_not_500(client, owner_project, method, path, big, expected):
    owner, project = owner_project
    url = path.format(id=big, pid=project.id)
    body = {"content": "c"} if method == "PATCH" else None

    res = client.request(method, url, headers=_auth(owner), json=body)

    assert res.status_code == expected, res.text
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


# page 위쪽 한도가 없어 OFFSET = (page-1)×size가 MariaDB 한도(2^64-1)를 넘으면 SQL 오류 → 500
# (core/pagination.py, A조). 목록 API 7개 공통. size=20이면 page ≈ 9.2×10^17, size=100이면 ≈ 1.8×10^17부터.
# 고치면 XPASS가 실패로 보이므로 그때 이 표시를 지운다. raises: 다른 이유의 실패를 흡수하지 않게.
_PAGE_OVERFLOW = pytest.mark.xfail(
    strict=True,
    raises=ProgrammingError,
    reason="D10-03: page 상한 없음 → OFFSET 범위 초과 500 (양준석 확인 요청)",
)


@pytest.mark.parametrize(
    ("param", "value", "size"),
    [
        pytest.param("page", str(10**30), None, marks=_PAGE_OVERFLOW, id="page-10^30"),
        pytest.param("page", str(10**18), None, marks=_PAGE_OVERFLOW, id="page-10^18"),
        pytest.param(
            "page", "190000000000000000", "100", marks=_PAGE_OVERFLOW, id="page-size100"
        ),
        ("page", "-1", None),
        ("page", "0", None),
        ("page", "abc", None),
        ("size", str(10**30), None),
        ("size", "-1", None),
        ("size", "0", None),
        ("size", "abc", None),
    ],
)
def test_page_size_out_of_range_422(client, owner_project, param, value, size):
    owner, project = owner_project
    params = {param: value} if size is None else {param: value, "size": size}

    res = client.get(
        f"/api/projects/{project.id}/tasks",
        headers=_auth(owner),
        params=params,
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
        ("\\", ["c\\d"]),
        ("/", ["a/b"]),
        ("없는말", []),
    ],
    ids=["sql", "percent", "underscore", "both", "backslash", "slash", "none"],
)
def test_search_q_sql_and_wildcards_literal(client, db, owner_project, q, expected):
    owner, project = owner_project
    for title in ("50%_할인", "일반", "c\\d", "a/b"):
        make_task(db, project, owner, title=title)

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
    """11/24 동작 고정: 업무 제목·댓글·이름 모두 저장되고 보낸 값 그대로 돌아온다(500·깨짐 없음).
    널 바이트를 거절하기로 정하면 이 테스트를 그때 고친다(명세에 규칙 없음)."""
    owner, project = owner_project
    headers = _auth(owner)

    task = client.post(
        f"/api/projects/{project.id}/tasks", headers=headers, json={"title": text}
    )
    assert task.status_code == 201, task.text
    assert task.json()["title"] == text
    tid = task.json()["id"]

    comment = client.post(
        f"/api/tasks/{tid}/comments", headers=headers, json={"content": text}
    )
    assert comment.status_code == 201, comment.text
    listed = client.get(f"/api/tasks/{tid}/comments", headers=headers).json()
    assert listed["items"][0]["content"] == text

    me = client.patch("/api/users/me", headers=headers, json={"name": text})
    assert me.status_code == 200, me.text
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


def test_project_update_my_role_rejected(client, db, owner_project):
    owner, project = owner_project
    name = project.name

    res = client.patch(
        f"/api/projects/{project.id}",
        headers=_auth(owner),
        json={"name": "바꿈", "my_role": "OWNER"},
    )

    assert res.status_code == 422
    db.expire_all()
    assert db.get(Project, project.id).name == name


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
    db.rollback()
    assert db.scalar(select(func.count()).select_from(TaskComment)) == 0


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
