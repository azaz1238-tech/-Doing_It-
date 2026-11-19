"""변경 이력 조회 API 테스트 (T-F4-05, LOG-03, API-SPEC §6 "변경 이력").

- GET /api/tasks/{task_id}/activities: 업무 하나의 이력
- GET /api/projects/{project_id}/activities: 프로젝트 최근 이력(삭제된 업무 포함)
- 둘 다 최신순(created_at DESC, id DESC), 페이지네이션(§1.3), 멤버 누구나(LOG-03-c 비멤버 403)
- Activity: task_title(삭제된 업무는 DELETED 행만 삭제 전 제목, 나머지 null — SPEC-CHANGELOG #20),
  user, old_assignee·new_assignee(field가 assignee_id일 때만 키가 있음)

이력은 실제 API(등록·수정·삭제·멤버 제거)로 쌓는다.
"""

import pytest
from sqlalchemy import event

from app.models import Project
from core.security import create_access_token
from tests.factories import add_member, make_project, make_user


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _brief(user) -> dict:
    return {"id": user.id, "login_id": user.login_id, "name": user.name}


def _task_acts_url(task_id: int) -> str:
    return f"/api/tasks/{task_id}/activities"


def _project_acts_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/activities"


@pytest.fixture
def team(db):
    """OWNER, MEMBER 2명(a·b), 비멤버. 업무는 각 테스트가 API로 만든다."""
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    member_a = make_user(db, name="민호")
    member_b = make_user(db, name="서연")
    outsider = make_user(db)
    add_member(db, project, member_a)
    add_member(db, project, member_b)
    return {
        "owner": owner,
        "a": member_a,
        "b": member_b,
        "outsider": outsider,
        "project_id": project.id,
    }


def _create_task(client, team, title="이력 업무", **fields) -> int:
    res = client.post(
        f"/api/projects/{team['project_id']}/tasks",
        headers=_auth(team["owner"]),
        json={"title": title, **fields},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _patch(client, team, task_id, **fields) -> None:
    res = client.patch(
        f"/api/tasks/{task_id}", headers=_auth(team["owner"]), json=fields
    )
    assert res.status_code == 200


def _get(client, url, user, **params) -> dict:
    res = client.get(url, headers=_auth(user), params=params)
    assert res.status_code == 200, res.text
    return res.json()


# --- 업무 이력 (LOG-03-a) ---


def test_task_activities_newest_first(client, team):
    """같은 초에 생긴 이력도 id 역순으로 흔들림 없이 최신순."""
    task_id = _create_task(client, team)
    _patch(client, team, task_id, status="DONE")
    _patch(client, team, task_id, priority="HIGH")

    body = _get(client, _task_acts_url(task_id), team["owner"])

    rows = [(i["action"], i["field"]) for i in body["items"]]
    assert rows == [("UPDATED", "priority"), ("UPDATED", "status"), ("CREATED", None)]
    ids = [i["id"] for i in body["items"]]
    assert ids == sorted(ids, reverse=True)
    assert body["total"] == 3 and body["page"] == 1 and body["size"] == 20


def test_activity_shape(client, team):
    task_id = _create_task(client, team, title="모양 확인")
    _patch(client, team, task_id, due_date="2026-11-25")

    item = _get(client, _task_acts_url(task_id), team["owner"])["items"][0]

    assert set(item) == {
        "id",
        "task_id",
        "task_title",
        "user",
        "action",
        "field",
        "old_value",
        "new_value",
        "created_at",
    }
    assert item["task_id"] == task_id and item["task_title"] == "모양 확인"
    assert item["user"] == _brief(team["owner"])
    assert (item["field"], item["old_value"], item["new_value"]) == (
        "due_date",
        None,
        "2026-11-25",
    )
    assert item["created_at"].endswith("Z")


def test_assignee_rows_have_briefs(client, team):
    task_id = _create_task(client, team, assignee_id=team["a"].id)
    _patch(client, team, task_id, assignee_id=team["b"].id, status="IN_PROGRESS")

    items = _get(client, _task_acts_url(task_id), team["owner"])["items"]
    by_field = {i["field"]: i for i in items if i["action"] == "UPDATED"}

    assignee_row = by_field["assignee_id"]
    assert assignee_row["old_assignee"] == _brief(team["a"])
    assert assignee_row["new_assignee"] == _brief(team["b"])
    assert "old_assignee" not in by_field["status"]
    assert "new_assignee" not in by_field["status"]


def test_assignee_cleared_new_assignee_null(client, team):
    task_id = _create_task(client, team, assignee_id=team["a"].id)
    _patch(client, team, task_id, assignee_id=None)

    row = _get(client, _task_acts_url(task_id), team["owner"])["items"][0]

    assert row["field"] == "assignee_id"
    assert row["old_assignee"] == _brief(team["a"])
    assert "new_assignee" in row and row["new_assignee"] is None


def test_removed_member_still_named(client, team):
    """멤버에서 제거된 사람도 이력에서 이름이 나온다(사용자 행은 지우지 않음)."""
    task_id = _create_task(client, team, assignee_id=team["a"].id)
    res = client.delete(
        f"/api/projects/{team['project_id']}/members/{team['a'].id}",
        headers=_auth(team["owner"]),
    )
    assert res.status_code == 204

    row = _get(client, _task_acts_url(task_id), team["owner"])["items"][0]

    assert row["field"] == "assignee_id"
    assert row["old_assignee"] == _brief(team["a"])
    assert row["new_assignee"] is None
    assert row["user"] == _brief(team["owner"])


# --- 프로젝트 최근 이력 (LOG-03-b) ---


def test_project_activities_recent_and_scoped(client, team, db):
    first = _create_task(client, team, title="첫째")
    second = _create_task(client, team, title="둘째")
    _patch(client, team, first, status="DONE")
    other_project = make_project(db, team["owner"])
    client.post(
        f"/api/projects/{other_project.id}/tasks",
        headers=_auth(team["owner"]),
        json={"title": "다른 프로젝트"},
    )

    body = _get(client, _project_acts_url(team["project_id"]), team["a"])

    rows = [(i["task_id"], i["task_title"], i["action"]) for i in body["items"]]
    assert rows == [
        (first, "첫째", "UPDATED"),
        (second, "둘째", "CREATED"),
        (first, "첫째", "CREATED"),
    ]
    assert body["total"] == 3 and body["size"] == 20


def test_deleted_task_titles(client, team):
    """삭제된 업무: DELETED 행만 삭제 전 제목, 같은 업무의 다른 행은 null (#20)."""
    task_id = _create_task(client, team, title="지울 업무")
    _patch(client, team, task_id, status="DONE")
    res = client.delete(f"/api/tasks/{task_id}", headers=_auth(team["owner"]))
    assert res.status_code == 204

    items = _get(client, _project_acts_url(team["project_id"]), team["owner"])["items"]

    rows = [(i["task_id"], i["task_title"], i["action"]) for i in items]
    assert rows == [
        (None, "지울 업무", "DELETED"),
        (None, None, "UPDATED"),
        (None, None, "CREATED"),
    ]
    gone = client.get(_task_acts_url(task_id), headers=_auth(team["owner"]))
    assert gone.status_code == 404 and gone.json()["code"] == "TASK_NOT_FOUND"


def test_paging_and_size_limit(client, team):
    task_id = _create_task(client, team)
    for status in ("IN_PROGRESS", "DONE", "TODO"):
        _patch(client, team, task_id, status=status)  # 이력 4행
    url = _task_acts_url(task_id)
    all_ids = [i["id"] for i in _get(client, url, team["owner"])["items"]]

    page2 = _get(client, url, team["owner"], page=2, size=2)
    far = _get(client, url, team["owner"], page=99)
    too_big = client.get(url, headers=_auth(team["owner"]), params={"size": 101})

    assert [i["id"] for i in page2["items"]] == all_ids[2:4]
    assert page2["total"] == 4 and page2["page"] == 2 and page2["size"] == 2
    assert far["items"] == [] and far["total"] == 4
    assert too_big.status_code == 422


# --- 권한·검사 순서 (LOG-03-c, §1.5) ---


@pytest.mark.parametrize("kind", ["task", "project"])
def test_activities_permissions(client, team, kind):
    task_id = _create_task(client, team)
    url = (
        _task_acts_url(task_id)
        if kind == "task"
        else _project_acts_url(team["project_id"])
    )
    missing = _task_acts_url(999_999) if kind == "task" else _project_acts_url(999_999)
    missing_code = "TASK_NOT_FOUND" if kind == "task" else "PROJECT_NOT_FOUND"

    no_token = client.get(url)
    outsider = client.get(url, headers=_auth(team["outsider"]))
    member = client.get(url, headers=_auth(team["b"]))
    not_found = client.get(missing, headers=_auth(team["outsider"]))

    assert no_token.status_code == 401
    assert outsider.status_code == 403
    assert outsider.json()["code"] == "NOT_PROJECT_MEMBER"
    assert "items" not in outsider.json()
    assert member.status_code == 200
    assert not_found.status_code == 404 and not_found.json()["code"] == missing_code


# --- 쿼리 수 (N+1 방지) ---


def _count_queries(engine, func) -> int:
    statements: list[str] = []

    def _before(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        func()
    finally:
        event.remove(engine, "before_cursor_execute", _before)
    return len(statements)


def test_query_count_constant(client, team, db, engine):
    """이력 행이 늘고 변경자·담당자가 모두 달라도 요청 1번의 SQL 수는 같다."""
    url = _project_acts_url(team["project_id"])

    def _add_rows(count: int) -> None:
        for _ in range(count):
            person = make_user(db)
            add_member(db, db.get(Project, team["project_id"]), person)
            res = client.post(
                f"/api/projects/{team['project_id']}/tasks",
                headers=_auth(person),
                json={"title": "작성자마다 다름", "assignee_id": person.id},
            )
            assert res.status_code == 201
            _patch(client, team, res.json()["id"], assignee_id=team["a"].id)

    _add_rows(1)
    small = _count_queries(engine, lambda: _get(client, url, team["owner"]))
    _add_rows(9)
    large = _count_queries(engine, lambda: _get(client, url, team["owner"]))

    assert _get(client, url, team["owner"])["total"] == 20
    assert large == small
