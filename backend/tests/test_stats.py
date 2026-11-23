"""마감 임박·지연 API (T-F5-05, DASH-03, API-SPEC §6). "오늘"은 get_today를 교체해 고정한다."""

from datetime import date

import pytest

from app.models.enums import TaskStatus
from core.clock import get_today
from core.security import create_access_token
from tests.factories import add_member, make_project, make_task, make_user

TODAY = date(2026, 11, 12)  # SPEC DASH-03-a 기준일


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _url(project_id) -> str:
    return f"/api/projects/{project_id}/stats/deadlines"


@pytest.fixture
def fixed_today(client):
    # client 픽스처가 테스트마다 앱을 새로 만들므로 따로 되돌리지 않아도 된다
    client.app.dependency_overrides[get_today] = lambda: TODAY


def _titles(items) -> list[str]:
    return [t["title"] for t in items]


def test_dash_03_a(client, db, fixed_today):  # SPEC DASH-03-a
    owner = make_user(db)
    project = make_project(db, owner)
    for title, due, status in [
        ("11/11", date(2026, 11, 11), TaskStatus.TODO),
        ("11/12", date(2026, 11, 12), TaskStatus.IN_PROGRESS),
        ("11/15", date(2026, 11, 15), TaskStatus.TODO),
        ("11/16", date(2026, 11, 16), TaskStatus.TODO),  # 오늘+4 → 제외
        ("11/13 완료", date(2026, 11, 13), TaskStatus.DONE),  # 완료 → 제외
        ("마감 없음", None, TaskStatus.TODO),  # 마감일 없음 → 제외
    ]:
        make_task(db, project, owner, title=title, due_date=due, status=status)

    res = client.get(_url(project.id), headers=_auth(owner))

    assert res.status_code == 200
    body = res.json()
    assert _titles(body["overdue"]) == ["11/11"]
    assert _titles(body["due_soon"]) == ["11/12", "11/15"]  # 오늘이면 임박, 마감일 순


def test_response_is_task_object(client, db, fixed_today):
    """항목은 Task 객체 (API-SPEC §4) — 담당자·작성자 포함."""
    owner = make_user(db)
    project = make_project(db, owner)
    make_task(db, project, owner, assignee_id=owner.id, due_date=TODAY)

    item = client.get(_url(project.id), headers=_auth(owner)).json()["due_soon"][0]

    assert item["assignee"]["id"] == owner.id
    assert item["created_by"]["id"] == owner.id
    assert item["due_date"] == "2026-11-12"


def test_order_by_due_date_then_id(client, db, fixed_today):
    owner = make_user(db)
    project = make_project(db, owner)
    make_task(db, project, owner, title="b", due_date=date(2026, 11, 13))
    make_task(db, project, owner, title="a", due_date=date(2026, 11, 13))
    make_task(db, project, owner, title="first", due_date=date(2026, 11, 12))
    make_task(db, project, owner, title="old", due_date=date(2026, 11, 1))
    make_task(db, project, owner, title="older", due_date=date(2026, 10, 1))

    body = client.get(_url(project.id), headers=_auth(owner)).json()

    assert _titles(body["overdue"]) == ["older", "old"]
    assert _titles(body["due_soon"]) == ["first", "b", "a"]  # 같은 날은 id 순


def test_excludes_other_projects(client, db, fixed_today):
    owner = make_user(db)
    project, other = make_project(db, owner), make_project(db, owner)
    make_task(db, other, owner, title="남의 것", due_date=TODAY)

    body = client.get(_url(project.id), headers=_auth(owner)).json()

    assert body == {"overdue": [], "due_soon": []}


def test_member_can_view(client, db, fixed_today):
    owner, member = make_user(db), make_user(db)
    project = make_project(db, owner)
    add_member(db, project, member)

    assert client.get(_url(project.id), headers=_auth(member)).status_code == 200


def test_non_member_403(client, db, fixed_today):  # 권한 실패 케이스 (CLAUDE.md §6)
    project = make_project(db, make_user(db))

    res = client.get(_url(project.id), headers=_auth(make_user(db)))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_project_not_found_404(client, db, fixed_today):
    res = client.get(_url(999999), headers=_auth(make_user(db)))

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


def test_without_token_401(client):
    assert client.get(_url(1)).status_code == 401
