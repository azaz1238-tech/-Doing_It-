"""담당자별 상태별 업무 수 API (T-F5-09, DASH-02, API-SPEC §6).

완료 기준: 담당자 × 상태 집계, "담당자 없음"도 따로 한 줄 (DASH-02-a).
          멤버 누구나, 비멤버 403, 페이지네이션 없음.
"""

from app.models.enums import ProjectRole, TaskStatus
from core.security import create_access_token
from tests.factories import add_member, make_project, make_task, make_user


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _url(project_id) -> str:
    return f"/api/projects/{project_id}/stats/assignees"


def _tasks(db, project, creator, assignee, status, n) -> None:
    for _ in range(n):
        make_task(
            db,
            project,
            creator,
            assignee_id=None if assignee is None else assignee.id,
            status=status,
        )


def _row(item) -> tuple:
    who = None if item["assignee"] is None else item["assignee"]["name"]
    return who, item["todo"], item["in_progress"], item["done"]


# --- 성공 ---


def test_dash_02_a_counts_with_unassigned(client, db):  # SPEC DASH-02-a
    jisu = make_user(db, name="지수")
    minho = make_user(db, name="민호")
    seoyeon = make_user(db, name="서연")
    project = make_project(db, jisu)
    add_member(db, project, minho, ProjectRole.MEMBER)
    add_member(db, project, seoyeon, ProjectRole.MEMBER)
    _tasks(db, project, jisu, minho, TaskStatus.TODO, 2)
    _tasks(db, project, jisu, minho, TaskStatus.DONE, 1)
    _tasks(db, project, jisu, seoyeon, TaskStatus.IN_PROGRESS, 1)
    _tasks(db, project, jisu, None, TaskStatus.TODO, 2)  # 담당자 없음

    res = client.get(_url(project.id), headers=_auth(jisu))

    assert res.status_code == 200
    # 이름 순(민호 < 서연), 담당자 없음은 맨 뒤. 업무 없는 지수는 줄이 없다
    assert [_row(i) for i in res.json()["items"]] == [
        ("민호", 2, 0, 1),
        ("서연", 0, 1, 0),
        (None, 2, 0, 0),
    ]


def test_response_shape_no_pagination(client, db):
    jisu = make_user(db, login_id="jisu", name="지수")
    project = make_project(db, jisu)
    _tasks(db, project, jisu, jisu, TaskStatus.TODO, 1)

    res = client.get(_url(project.id), headers=_auth(jisu))

    body = res.json()
    assert set(body) == {"items"}  # 집계라 page·total 없음 (API-SPEC §1.3)
    item = body["items"][0]
    assert set(item) == {"assignee", "todo", "in_progress", "done"}
    assert item["assignee"] == {"id": jisu.id, "login_id": "jisu", "name": "지수"}
    assert all(isinstance(item[k], int) for k in ("todo", "in_progress", "done"))
    assert "password_hash" not in res.text


def test_same_name_ordered_by_id(client, db):
    jisu = make_user(db)
    first = make_user(db, name="김철수")
    second = make_user(db, name="김철수")
    project = make_project(db, jisu)
    add_member(db, project, first, ProjectRole.MEMBER)
    add_member(db, project, second, ProjectRole.MEMBER)
    _tasks(db, project, jisu, second, TaskStatus.TODO, 1)
    _tasks(db, project, jisu, first, TaskStatus.TODO, 1)

    items = client.get(_url(project.id), headers=_auth(jisu)).json()["items"]

    assert [i["assignee"]["id"] for i in items] == [first.id, second.id]


def test_excludes_other_projects(client, db):
    jisu = make_user(db)
    project = make_project(db, jisu)
    other = make_project(db, jisu)
    _tasks(db, project, jisu, jisu, TaskStatus.TODO, 1)
    _tasks(db, other, jisu, jisu, TaskStatus.TODO, 5)
    _tasks(db, other, jisu, None, TaskStatus.DONE, 3)

    items = client.get(_url(project.id), headers=_auth(jisu)).json()["items"]

    assert len(items) == 1
    assert (items[0]["todo"], items[0]["in_progress"], items[0]["done"]) == (1, 0, 0)


def test_no_tasks_empty_items(client, db):
    jisu = make_user(db)
    project = make_project(db, jisu)

    res = client.get(_url(project.id), headers=_auth(jisu))

    assert res.status_code == 200
    assert res.json() == {"items": []}


def test_member_can_view(client, db):
    jisu, minho = make_user(db), make_user(db)
    project = make_project(db, jisu)
    add_member(db, project, minho, ProjectRole.MEMBER)
    _tasks(db, project, jisu, None, TaskStatus.TODO, 1)

    res = client.get(_url(project.id), headers=_auth(minho))

    assert res.status_code == 200
    assert len(res.json()["items"]) == 1


# --- 실패 ---


def test_non_member_403(client, db):  # 권한 실패 케이스 (CLAUDE.md §6)
    jisu, outsider = make_user(db), make_user(db)
    project = make_project(db, jisu)
    _tasks(db, project, jisu, jisu, TaskStatus.TODO, 1)

    res = client.get(_url(project.id), headers=_auth(outsider))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_project_not_found_404(client, db):
    jisu = make_user(db)

    res = client.get(_url(999_999), headers=_auth(jisu))

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


def test_without_token_401(client):
    res = client.get(_url(1))

    assert res.status_code == 401
