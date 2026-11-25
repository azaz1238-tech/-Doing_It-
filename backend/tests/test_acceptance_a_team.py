"""A조 수용 기준 회귀 테스트 보강 (D10-01, SPEC §11).

김서현 결과서(docs/reports/2026-11-24-acceptance-a-team.md)의 35개 시나리오를 기존 pytest와 대조했다
(docs/reports/2026-11-24-acceptance-a-team-regression.md). API로 확인할 수 있는데 기존 테스트가
지키지 않던 부분만 여기에 둔다. 기존 파일(A조 담당)은 고치지 않는다.
"""

from datetime import date

from tests.factories import add_member, make_project, make_user
from tests.factories import auth_header as _auth

PROJECTS = "/api/projects"


def test_auth_01_a_signup_then_login(client):
    """AUTH-01-a: 가입한 계정으로 바로 로그인된다 (가입 → 로그인 → 내 정보)."""
    body = {"login_id": "jisoo01", "password": "password123", "name": "지수"}
    assert client.post("/api/auth/signup", json=body).status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"login_id": "jisoo01", "password": "password123"},
    )

    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["login_id"] == "jisoo01"
    assert me.json()["name"] == "지수"


def test_prj_02_a_list_card_has_name_period_role(client, db):
    """PRJ-02-a: 목록 카드마다 이름·기간·내 역할 (기존 테스트는 id·역할만 확인)."""
    owner, minho = make_user(db), make_user(db)
    project = make_project(
        db,
        owner,
        name="동잇 개발",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 26),
    )
    add_member(db, project, minho)

    items = client.get(PROJECTS, headers=_auth(minho)).json()["items"]

    assert len(items) == 1
    card = items[0]
    assert card["name"] == "동잇 개발"
    assert (card["start_date"], card["end_date"]) == ("2026-11-10", "2026-11-26")
    assert card["my_role"] == "MEMBER"


def test_prj_03_b_member_update_rejected_and_unchanged(client, db):
    """PRJ-03-b: MEMBER의 수정 시도는 403이고, 이름·설명은 그대로 남는다."""
    owner, minho = make_user(db), make_user(db)
    project = make_project(db, owner, name="동잇 개발", description="원래 설명")
    add_member(db, project, minho)

    res = client.patch(
        f"{PROJECTS}/{project.id}",
        headers=_auth(minho),
        json={"name": "바꿈", "description": "바꾼 설명"},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
    detail = client.get(f"{PROJECTS}/{project.id}", headers=_auth(owner)).json()
    assert detail["name"] == "동잇 개발"
    assert detail["description"] == "원래 설명"
