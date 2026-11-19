"""프로젝트 생성·목록·상세·수정·삭제 API (T-F2-02·03·04, PRJ-01·02·07·03, API-SPEC §5.2).

완료 기준: 내 프로젝트만, 최근 생성순(T-F2-02) / 비멤버 403(T-F2-03) / MEMBER 403(T-F2-04).
"""

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models import Project, ProjectMember, Task, TaskActivity
from app.models.enums import ActivityAction, ProjectRole, TaskStatus
from core.security import create_access_token
from tests.factories import add_member, make_project, make_task, make_user

URL = "/api/projects"
NAME_MESSAGE = "프로젝트 이름은 1~30자로 입력해 주세요"
PERIOD_MESSAGE = "종료일은 시작일 이후여야 합니다"


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


# --- 생성 (PRJ-01) ---


def test_create_201_creator_is_owner(client, db):  # PRJ-01-a
    user = make_user(db)

    res = client.post(
        URL,
        headers=_auth(user),
        json={
            "name": "  동잇 개발 ",
            "description": "11월 팀 프로젝트",
            "start_date": "2026-11-10",
            "end_date": "2026-11-26",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert set(body) == {
        "id",
        "name",
        "description",
        "start_date",
        "end_date",
        "my_role",
        "progress",  # DASH-01
        "created_at",
        "updated_at",
    }
    assert body["name"] == "동잇 개발"
    assert body["start_date"] == "2026-11-10"
    assert body["my_role"] == "OWNER"
    assert body["created_at"].endswith("Z")
    # user.id를 읽을 때 열린 트랜잭션은 REPEATABLE READ라 API가 넣은 행을 못 본다 → 끝내고 다시 조회
    db.rollback()
    member = db.scalars(
        select(ProjectMember).where(ProjectMember.project_id == body["id"])
    ).one()
    assert (member.user_id, member.role) == (user.id, "OWNER")


def test_create_name_only_201(client, db):
    res = client.post(URL, headers=_auth(make_user(db)), json={"name": "가" * 30})

    assert res.status_code == 201
    body = res.json()
    assert body["description"] is None
    assert body["start_date"] is None
    assert body["end_date"] is None


def test_create_same_start_and_end_201(client, db):
    res = client.post(
        URL,
        headers=_auth(make_user(db)),
        json={"name": "p", "start_date": "2026-11-26", "end_date": "2026-11-26"},
    )
    assert res.status_code == 201


@pytest.mark.parametrize("name", ["", "   ", "가" * 31])
def test_create_name_length_422(client, db, name):  # PRJ-01-b
    res = client.post(URL, headers=_auth(make_user(db)), json={"name": name})

    assert res.status_code == 422
    assert res.json()["errors"] == [{"field": "name", "message": NAME_MESSAGE}]


def test_create_period_reversed_422(client, db):  # PRJ-01-c
    res = client.post(
        URL,
        headers=_auth(make_user(db)),
        json={"name": "p", "start_date": "2026-11-26", "end_date": "2026-11-10"},
    )

    assert res.status_code == 422
    assert res.json()["errors"] == [{"field": "end_date", "message": PERIOD_MESSAGE}]


def test_create_without_token_401(client):
    assert client.post(URL, json={"name": "p"}).status_code == 401


def test_create_without_token_bad_body_401(client):
    """토큰 검사가 본문 검증보다 먼저 (API-SPEC §1.5)"""
    assert client.post(URL, json={"name": ""}).status_code == 401


# --- 목록 (PRJ-02) ---


def test_list_only_my_projects_with_role(client, db):  # PRJ-02-a
    me, other = make_user(db), make_user(db)
    mine = make_project(db, me)
    joined = make_project(db, other)
    add_member(db, joined, me)
    make_project(db, other)  # 내가 멤버가 아닌 프로젝트

    res = client.get(URL, headers=_auth(me))

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    roles = {p["id"]: p["my_role"] for p in body["items"]}
    assert roles == {mine.id: "OWNER", joined.id: "MEMBER"}


def test_list_latest_first(client, db):
    me = make_user(db)
    ids = [make_project(db, me).id for _ in range(3)]

    items = client.get(URL, headers=_auth(me)).json()["items"]

    assert [p["id"] for p in items] == ids[::-1]


def test_list_empty(client, db):  # PRJ-02-b
    body = client.get(URL, headers=_auth(make_user(db))).json()
    assert body == {"items": [], "total": 0, "page": 1, "size": 20}


def test_list_pagination(client, db):
    me = make_user(db)
    for _ in range(3):
        make_project(db, me)

    body = client.get(URL, headers=_auth(me), params={"page": 2, "size": 2}).json()

    assert (len(body["items"]), body["total"], body["page"], body["size"]) == (
        1,
        3,
        2,
        2,
    )


def test_list_without_token_401(client):
    assert client.get(URL).status_code == 401


# --- 상세 (PRJ-07) ---


def test_detail_200_for_member(client, db):
    owner, member = make_user(db), make_user(db)
    project = make_project(db, owner, name="동잇 개발")
    add_member(db, project, member)

    res = client.get(f"{URL}/{project.id}", headers=_auth(member))

    assert res.status_code == 200
    assert res.json()["name"] == "동잇 개발"
    assert res.json()["my_role"] == "MEMBER"


def test_detail_non_member_403(client, db):  # PRJ-07-a
    owner, outsider = make_user(db), make_user(db)
    project = make_project(db, owner, name="비밀 프로젝트")

    res = client.get(f"{URL}/{project.id}", headers=_auth(outsider))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"
    assert "비밀 프로젝트" not in res.text  # 이름조차 보이지 않는다


def test_detail_not_found_404(client, db):
    res = client.get(f"{URL}/999999", headers=_auth(make_user(db)))

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_detail_update_delete_without_token_401(client, method):
    # 검사 순서 401 → 404: 없는 프로젝트여도 토큰이 없으면 401 (D8-02)
    kwargs = {"json": {"name": "x"}} if method == "patch" else {}
    res = getattr(client, method)(f"{URL}/999999", **kwargs)

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


# --- 수정 (PRJ-03) ---


def _project_with_period(db):
    owner = make_user(db)
    project = make_project(
        db,
        owner,
        name="동잇 개발",
        description="11월",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 26),
    )
    return owner, project


def test_update_only_sent_fields(client, db):
    owner, project = _project_with_period(db)

    res = client.patch(
        f"{URL}/{project.id}", headers=_auth(owner), json={"name": " 새 이름 "}
    )

    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "새 이름"
    assert body["description"] == "11월"
    assert (body["start_date"], body["end_date"]) == ("2026-11-10", "2026-11-26")
    assert body["my_role"] == "OWNER"


def test_update_null_clears_optional_fields(client, db):
    owner, project = _project_with_period(db)

    res = client.patch(
        f"{URL}/{project.id}",
        headers=_auth(owner),
        json={"description": None, "start_date": None},
    )

    assert res.status_code == 200
    assert res.json()["description"] is None
    assert res.json()["start_date"] is None


def test_update_empty_body_200(client, db):
    owner, project = _project_with_period(db)

    res = client.patch(f"{URL}/{project.id}", headers=_auth(owner), json={})

    assert res.status_code == 200
    assert res.json()["name"] == "동잇 개발"


def test_update_end_before_saved_start_422(client, db):
    """end_date만 보내도 저장된 start_date와 비교한다 (최종 값 기준)"""
    owner, project = _project_with_period(db)

    res = client.patch(
        f"{URL}/{project.id}", headers=_auth(owner), json={"end_date": "2026-11-01"}
    )

    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"
    assert res.json()["errors"] == [{"field": "end_date", "message": PERIOD_MESSAGE}]


def test_update_both_dates_reversed_422(client, db):
    owner, project = _project_with_period(db)

    res = client.patch(
        f"{URL}/{project.id}",
        headers=_auth(owner),
        json={"start_date": "2026-11-26", "end_date": "2026-11-10"},
    )

    assert res.status_code == 422
    assert res.json()["errors"] == [{"field": "end_date", "message": PERIOD_MESSAGE}]


@pytest.mark.parametrize("name", [None, "", "가" * 31])
def test_update_name_invalid_422(client, db, name):
    owner, project = _project_with_period(db)

    res = client.patch(f"{URL}/{project.id}", headers=_auth(owner), json={"name": name})

    assert res.status_code == 422
    assert res.json()["errors"] == [{"field": "name", "message": NAME_MESSAGE}]


def test_update_by_member_403(client, db):  # PRJ-03-b
    _, project = _project_with_period(db)
    member = make_user(db)
    add_member(db, project, member)

    res = client.patch(
        f"{URL}/{project.id}", headers=_auth(member), json={"name": "바꿈"}
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_update_by_non_member_403(client, db):
    _, project = _project_with_period(db)

    res = client.patch(
        f"{URL}/{project.id}", headers=_auth(make_user(db)), json={"name": "바꿈"}
    )

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_update_not_found_404(client, db):
    res = client.patch(
        f"{URL}/999999", headers=_auth(make_user(db)), json={"name": "바꿈"}
    )
    assert res.status_code == 404


# --- 삭제 (PRJ-03) ---


def test_delete_204_cascades(client, db):  # PRJ-03-a
    owner, member = make_user(db), make_user(db)
    project = make_project(db, owner)
    add_member(db, project, member)
    task = make_task(db, project, owner)
    db.add(
        TaskActivity(
            task_id=task.id,
            project_id=project.id,
            user_id=owner.id,
            action=ActivityAction.CREATED,
        )
    )
    db.commit()
    project_id = project.id

    res = client.delete(f"{URL}/{project_id}", headers=_auth(owner))

    assert res.status_code == 204
    assert res.content == b""
    assert client.get(f"{URL}/{project_id}", headers=_auth(owner)).status_code == 404
    db.rollback()  # API가 지운 결과를 보려고 테스트 세션의 트랜잭션을 끝낸다
    for model in (Project, ProjectMember, Task, TaskActivity):
        assert db.scalar(select(func.count()).select_from(model)) == 0


def test_delete_by_member_403(client, db):  # PRJ-03-b
    owner, member = make_user(db), make_user(db)
    project = make_project(db, owner)
    add_member(db, project, member)

    res = client.delete(f"{URL}/{project.id}", headers=_auth(member))

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
    assert client.get(f"{URL}/{project.id}", headers=_auth(owner)).status_code == 200


def test_delete_by_non_member_403(client, db):
    project = make_project(db, make_user(db))

    res = client.delete(f"{URL}/{project.id}", headers=_auth(make_user(db)))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_delete_not_found_404(client, db):
    res = client.delete(f"{URL}/999999", headers=_auth(make_user(db)))
    assert res.status_code == 404


def test_second_owner_can_delete(client, db):
    """역할로 판단한다 — 만든 사람이 아니어도 OWNER면 삭제할 수 있다"""
    creator, co_owner = make_user(db), make_user(db)
    project = make_project(db, creator)
    add_member(db, project, co_owner, role=ProjectRole.OWNER)

    res = client.delete(f"{URL}/{project.id}", headers=_auth(co_owner))

    assert res.status_code == 204


# --- 진행률 (DASH-01, T-F5-01) ---


def _project_with_tasks(db, done: int, todo: int):
    owner = make_user(db)
    project = make_project(db, owner)
    for _ in range(done):
        make_task(db, project, owner, status=TaskStatus.DONE)
    for _ in range(todo):
        make_task(db, project, owner)
    return owner, project


def test_progress_list_and_detail_40_percent(client, db):  # DASH-01-a
    owner, project = _project_with_tasks(db, done=4, todo=6)
    expected = {"total": 10, "done": 4, "percent": 40}

    listed = client.get(URL, headers=_auth(owner)).json()["items"][0]
    detail = client.get(f"{URL}/{project.id}", headers=_auth(owner)).json()

    assert listed["progress"] == expected
    assert detail["progress"] == expected


def test_progress_no_tasks_0_percent(client, db):  # DASH-01-a 예외
    owner, project = _project_with_tasks(db, done=0, todo=0)

    res = client.get(f"{URL}/{project.id}", headers=_auth(owner))

    assert res.json()["progress"] == {"total": 0, "done": 0, "percent": 0}


@pytest.mark.parametrize(
    ("done", "todo", "percent"), [(1, 2, 33), (2, 1, 67), (1, 7, 13), (3, 0, 100)]
)
def test_progress_rounding(client, db, done, todo, percent):
    owner, project = _project_with_tasks(db, done=done, todo=todo)

    res = client.get(f"{URL}/{project.id}", headers=_auth(owner))

    assert res.json()["progress"]["percent"] == percent


def test_progress_counts_each_project_separately(client, db):
    """목록에서 프로젝트끼리 섞이지 않는다 (한 쿼리로 묶어 셈)."""
    owner, a = _project_with_tasks(db, done=1, todo=1)
    b = make_project(db, owner)
    make_task(db, b, owner, status=TaskStatus.DONE)

    items = client.get(URL, headers=_auth(owner)).json()["items"]
    by_id = {item["id"]: item["progress"]["percent"] for item in items}

    assert by_id == {a.id: 50, b.id: 100}


def test_create_returns_zero_progress(client, db):
    res = client.post(URL, headers=_auth(make_user(db)), json={"name": "p"})

    assert res.json()["progress"] == {"total": 0, "done": 0, "percent": 0}
