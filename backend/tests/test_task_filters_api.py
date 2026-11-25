"""업무 검색·필터 테스트 (T-F5-03, TASK-07, API-SPEC §5.4 GET /projects/{id}/tasks).

쿼리: q(제목 부분 일치) · assignee_id(숫자 또는 none) · priority · due_from·due_to(양 끝 포함).
- 여러 조건은 모두 만족하는 업무만(TASK-07-a). 맞는 업무가 없으면 빈 목록(TASK-07-c).
- total도 걸러진 개수. 필터는 권한 검사 뒤에 적용(비멤버는 403).
- q의 %·_는 글자 그대로 찾는다. 앞뒤 공백만 있으면 조건 없음.
- 멤버가 아닌 담당자 id, due_from > due_to는 오류가 아니라 빈 결과(조건을 그대로 적용).

업무는 factories.make_task로 직접 만든다(필터 대상 값만 필요, 이력은 이 테스트의 관심 밖).
"""

from datetime import date

import pytest

from tests.factories import add_member, make_project, make_task, make_user
from tests.factories import auth_header as _auth


@pytest.fixture
def team(db):
    """OWNER 지수, MEMBER 민호·서연, 비멤버. 업무는 각 테스트가 만든다."""
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    minho = make_user(db, name="민호")
    seoyeon = make_user(db, name="서연")
    add_member(db, project, minho)
    add_member(db, project, seoyeon)
    return {
        "owner": owner,
        "minho": minho,
        "seoyeon": seoyeon,
        "outsider": make_user(db),
        "project": project,
    }


def _task(db, team, title="업무", **fields):
    return make_task(db, team["project"], team["owner"], title=title, **fields)


def _list(client, team, **params) -> dict:
    res = client.get(
        f"/api/projects/{team['project'].id}/tasks",
        headers=_auth(team["owner"]),
        params=params,
    )
    assert res.status_code == 200, res.text
    return res.json()


def _titles(body: dict) -> list[str]:
    return sorted(item["title"] for item in body["items"])


def test_assignee_and_priority_combined(client, db, team):
    """TASK-07-a: 담당자 민호 + 우선순위 긴급 → 두 조건을 모두 만족하는 것만."""
    _task(db, team, "민호 긴급", assignee_id=team["minho"].id, priority="URGENT")
    _task(db, team, "민호 낮음", assignee_id=team["minho"].id, priority="LOW")
    _task(db, team, "서연 긴급", assignee_id=team["seoyeon"].id, priority="URGENT")

    body = _list(client, team, assignee_id=team["minho"].id, priority="URGENT")

    assert _titles(body) == ["민호 긴급"]
    assert body["total"] == 1


def test_q_partial_case_insensitive(client, db, team):
    for title in ("로그인 API", "api 문서", "회의"):
        _task(db, team, title)

    assert _titles(_list(client, team, q="Api")) == ["api 문서", "로그인 API"]


def test_q_wildcards_are_literal(client, db, team):
    for title in ("100%", "1000", "a_b", "axb"):
        _task(db, team, title)

    assert _titles(_list(client, team, q="%")) == ["100%"]
    assert _titles(_list(client, team, q="_")) == ["a_b"]


def test_q_blank_is_ignored(client, db, team):
    _task(db, team, "하나")
    _task(db, team, "둘")

    assert _list(client, team, q="   ")["total"] == 2


def test_assignee_none_only_unassigned(client, db, team):
    _task(db, team, "담당 있음", assignee_id=team["minho"].id)
    _task(db, team, "담당 없음")

    assert _titles(_list(client, team, assignee_id="none")) == ["담당 없음"]


def test_due_range_inclusive_and_excludes_no_due(client, db, team):
    _task(db, team, "20일", due_date=date(2026, 11, 20))
    _task(db, team, "22일", due_date=date(2026, 11, 22))
    _task(db, team, "25일", due_date=date(2026, 11, 25))
    _task(db, team, "마감 없음")

    both = _list(client, team, due_from="2026-11-20", due_to="2026-11-22")
    from_only = _list(client, team, due_from="2026-11-22")
    to_only = _list(client, team, due_to="2026-11-20")

    assert _titles(both) == ["20일", "22일"]
    assert _titles(from_only) == ["22일", "25일"]
    assert _titles(to_only) == ["20일"]


def test_due_from_after_due_to_is_empty(client, db, team):
    _task(db, team, "22일", due_date=date(2026, 11, 22))

    body = _list(client, team, due_from="2026-11-25", due_to="2026-11-20")

    assert body["items"] == [] and body["total"] == 0


def test_filters_with_status_total_and_paging(client, db, team):
    """total은 걸러진 개수(컬럼 머리 개수·더 보기에 씀). 상태·페이지와 함께 동작."""
    for i in range(3):
        _task(db, team, f"보고서 {i}")
    _task(db, team, "보고서 완료", status="DONE")
    _task(db, team, "회의록")

    todo = _list(client, team, status="TODO", q="보고서")
    page2 = _list(client, team, status="TODO", q="보고서", page=2, size=2)

    assert todo["total"] == 3
    assert _titles(todo) == ["보고서 0", "보고서 1", "보고서 2"]
    assert len(page2["items"]) == 1 and page2["total"] == 3


def test_no_match_returns_empty(client, db, team):
    """TASK-07-c: 어떤 업무와도 맞지 않으면 빈 목록(화면이 안내를 띄움)."""
    _task(db, team, "업무")

    body = _list(client, team, q="없는 제목")

    assert body == {"items": [], "total": 0, "page": 1, "size": 20}


def test_non_member_assignee_id_is_empty_not_400(client, db, team):
    _task(db, team, "업무", assignee_id=team["minho"].id)

    body = _list(client, team, assignee_id=team["outsider"].id)

    assert body["total"] == 0


@pytest.mark.parametrize(
    ("param", "value"),
    [
        ("assignee_id", "abc"),
        ("assignee_id", "9" * 5000),  # int() 자릿수 한도를 넘는 숫자도 500이 아니라 422
        ("priority", "urgent"),
        ("due_from", "2026-13-01"),
    ],
)
def test_bad_filter_values_422(client, team, param, value):
    res = client.get(
        f"/api/projects/{team['project'].id}/tasks",
        headers=_auth(team["owner"]),
        params={param: value},
    )

    assert res.status_code == 422
    assert param in [e["field"] for e in res.json()["errors"]]


def test_filters_do_not_bypass_membership(client, db, team):
    _task(db, team, "업무")

    res = client.get(
        f"/api/projects/{team['project'].id}/tasks",
        headers=_auth(team["outsider"]),
        params={"q": "업무", "assignee_id": "none"},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"
