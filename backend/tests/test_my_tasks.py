"""내 업무 대시보드 API (T-F5-07, DASH-04, API-SPEC §6). "오늘"은 get_today를 교체해 고정한다."""

from datetime import date

import pytest

from app.models.enums import TaskStatus
from core.clock import get_today
from core.security import create_access_token
from tests.factories import add_member, make_project, make_task, make_user

URL = "/api/users/me/tasks"
TODAY = date(2026, 11, 12)


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def fixed_today(client):
    # client 픽스처가 테스트마다 앱을 새로 만들므로 따로 되돌리지 않아도 된다
    client.app.dependency_overrides[get_today] = lambda: TODAY


def _setup(db, n_projects=1):
    """owner가 만든 프로젝트들에 minho를 멤버로 넣는다."""
    owner, minho = make_user(db), make_user(db)
    projects = [make_project(db, owner) for _ in range(n_projects)]
    for p in projects:
        add_member(db, p, minho)
    return owner, minho, projects


def test_dash_04_a_order_and_project(client, db, fixed_today):  # SPEC DASH-04-a
    owner, minho, (p1, p2, p3) = _setup(db, 3)

    def task(project, title, due):
        make_task(db, project, owner, title=title, assignee_id=minho.id, due_date=due)

    task(p1, "나머지-마감없음", None)
    task(p2, "나머지-11/20", date(2026, 11, 20))
    task(p3, "임박-11/15", date(2026, 11, 15))
    task(p1, "지연-11/10", date(2026, 11, 10))
    task(p2, "임박-오늘", date(2026, 11, 12))
    task(p3, "지연-11/01", date(2026, 11, 1))

    res = client.get(URL, headers=_auth(minho))

    assert res.status_code == 200
    items = res.json()["items"]
    assert [i["title"] for i in items] == [
        "지연-11/01",
        "지연-11/10",
        "임박-오늘",
        "임박-11/15",
        "나머지-11/20",
        "나머지-마감없음",
    ]
    assert [i["alert"] for i in items] == [
        "OVERDUE",
        "OVERDUE",
        "DUE_SOON",
        "DUE_SOON",
        None,
        None,
    ]
    assert items[0]["project"] == {"id": p3.id, "name": p3.name}
    # Task 객체 필드는 그대로 (API-SPEC §4)
    assert items[0]["assignee"]["id"] == minho.id
    assert items[0]["created_by"]["id"] == owner.id


def test_due_soon_boundary(client, db, fixed_today):
    """오늘+3일은 임박, 오늘+4일은 경고 없음 (DASH-03과 같은 기준)."""
    owner, minho, (p,) = _setup(db)
    make_task(
        db, p, owner, title="+3", assignee_id=minho.id, due_date=date(2026, 11, 15)
    )
    make_task(
        db, p, owner, title="+4", assignee_id=minho.id, due_date=date(2026, 11, 16)
    )

    items = client.get(URL, headers=_auth(minho)).json()["items"]

    assert [(i["title"], i["alert"]) for i in items] == [
        ("+3", "DUE_SOON"),
        ("+4", None),
    ]


def test_dash_04_b_done_excluded_and_empty(client, db, fixed_today):  # SPEC DASH-04-b
    owner, minho, (p,) = _setup(db)
    make_task(
        db, p, owner, assignee_id=minho.id, status=TaskStatus.DONE, due_date=TODAY
    )

    body = client.get(URL, headers=_auth(minho)).json()

    assert body == {"items": [], "total": 0, "page": 1, "size": 20}


def test_only_my_tasks(client, db, fixed_today):
    owner, minho, (p,) = _setup(db)
    make_task(db, p, owner, title="남의 것", assignee_id=owner.id)
    make_task(db, p, owner, title="담당 없음")

    assert client.get(URL, headers=_auth(minho)).json()["total"] == 0


def test_not_member_project_excluded(client, db, fixed_today):
    """멤버가 아닌 프로젝트의 업무는 담당으로 남아 있어도 보이지 않는다(방어)."""
    owner, minho = make_user(db), make_user(db)
    p = make_project(db, owner)  # minho는 멤버 아님
    make_task(db, p, owner, assignee_id=minho.id)

    assert client.get(URL, headers=_auth(minho)).json()["total"] == 0


def test_pagination(client, db, fixed_today):
    owner, minho, (p,) = _setup(db)
    for i in range(3):
        make_task(db, p, owner, title=f"t{i}", assignee_id=minho.id)

    body = client.get(URL, params={"page": 2, "size": 2}, headers=_auth(minho)).json()

    assert body["total"] == 3
    assert [i["title"] for i in body["items"]] == ["t2"]


def test_without_token_401(client):
    assert client.get(URL).status_code == 401
