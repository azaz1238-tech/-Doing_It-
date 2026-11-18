"""업무 API 테스트 (T-F2-07~09·T-F3-04, API-SPEC §5.4·§10).

§10 필수: 등록 201 + CREATED 이력 1건, 제목 31자 422, 상태+담당자 동시 변경 시 이력 2건,
DONE 전환 시 completed_at 기록·해제, 삭제 후 이력 task_id NULL 유지, 비멤버 업무 조회 403,
MEMBER의 타인 업무 수정·삭제 403, 담당자 상태 변경 성공·다른 필드 403,
작성자도 담당자도 아닌 MEMBER의 상태 변경 403, 토큰 없이 잘못된 본문 401,
비멤버 담당자 400(ASSIGNEE_NOT_MEMBER, 맨 아래).

API가 쓴 데이터를 db 픽스처로 읽기 전에는 db.rollback()으로 트랜잭션을 끝낸다
(REPEATABLE READ라 열린 트랜잭션은 새 행을 못 본다).
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.models import Task, TaskActivity
from app.models.enums import TaskPriority
from core.security import create_access_token
from tests.factories import add_member, make_project, make_task, make_user


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _tasks_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/tasks"


def _task_url(task_id: int) -> str:
    return f"/api/tasks/{task_id}"


def _activities(db) -> list[TaskActivity]:
    db.rollback()
    return list(db.scalars(select(TaskActivity).order_by(TaskActivity.id)))


@pytest.fixture
def team(db):
    """OWNER, 작성자 MEMBER, 담당자 MEMBER, 그 외 MEMBER, 비멤버 + 작성자가 만든 업무 1개."""
    owner = make_user(db)
    project = make_project(db, owner)
    author, assignee, other, outsider = (make_user(db) for _ in range(4))
    for user in (author, assignee, other):
        add_member(db, project, user)
    task = make_task(db, project, author, title="원래 제목", assignee_id=assignee.id)
    return {
        "project": project,
        "owner": owner,
        "author": author,
        "assignee": assignee,
        "other": other,
        "outsider": outsider,
        "task": task,
        # 응답을 읽은 뒤 rollback해도 id를 다시 읽지 않도록 미리 꺼내 둔다
        "project_id": project.id,
        "task_id": task.id,
    }


# --- 등록 (TASK-01) ---


def test_create_201_with_created_activity(client, db):
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    member = make_user(db, name="민호")
    add_member(db, project, member)

    res = client.post(
        _tasks_url(project.id),
        headers=_auth(owner),
        json={
            "title": "  로그인 API 구현 ",
            "description": "JWT 발급까지",
            "assignee_id": member.id,
            "due_date": "2026-11-14",
            "priority": "HIGH",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "로그인 API 구현"
    assert body["status"] == "TODO"
    assert body["priority"] == "HIGH"
    assert body["due_date"] == "2026-11-14"
    assert body["assignee"] == {
        "id": member.id,
        "login_id": member.login_id,
        "name": "민호",
    }
    assert body["created_by"]["name"] == "지수"
    assert body["completed_at"] is None
    assert body["created_at"].endswith("Z")
    [row] = _activities(db)
    assert (row.action, row.field, row.task_id) == ("CREATED", None, body["id"])


def test_create_title_31_chars_422(client, db):
    owner = make_user(db)
    project = make_project(db, owner)

    res = client.post(
        _tasks_url(project.id), headers=_auth(owner), json={"title": "가" * 31}
    )

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert [e["field"] for e in body["errors"]] == ["title"]


def test_create_with_status_field_422(client, db):
    owner = make_user(db)
    project = make_project(db, owner)

    res = client.post(
        _tasks_url(project.id),
        headers=_auth(owner),
        json={"title": "t", "status": "DONE"},
    )

    assert res.status_code == 422


def test_create_without_token_bad_body_401(client, db):
    project = make_project(db, make_user(db))

    res = client.post(_tasks_url(project.id), json={"title": ""})

    assert res.status_code == 401


def test_create_non_member_403(client, team):
    res = client.post(
        _tasks_url(team["project_id"]),
        headers=_auth(team["outsider"]),
        json={"title": "t"},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_create_project_not_found_404(client, db):
    res = client.post(
        _tasks_url(999_999), headers=_auth(make_user(db)), json={"title": "t"}
    )

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


# --- 칸반 목록 (TASK-05) ---


def test_list_kanban_order_and_page_shape(client, db):
    owner = make_user(db)
    project = make_project(db, owner)
    specs = [
        ("low", TaskPriority.LOW, None),
        ("high-none", TaskPriority.HIGH, None),
        ("urgent", TaskPriority.URGENT, date(2026, 11, 30)),
        ("high-early", TaskPriority.HIGH, date(2026, 11, 20)),
    ]
    for title, priority, due in specs:
        make_task(db, project, owner, title=title, priority=priority, due_date=due)

    res = client.get(_tasks_url(project.id), headers=_auth(owner))

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert (body["total"], body["page"], body["size"]) == (4, 1, 20)
    assert [t["title"] for t in body["items"]] == [
        "urgent",
        "high-early",
        "high-none",
        "low",
    ]


def test_list_status_filter_and_paging(client, db):
    owner = make_user(db)
    project = make_project(db, owner)
    for i in range(3):
        make_task(db, project, owner, title=f"todo{i}")
    make_task(db, project, owner, title="done", status="DONE")

    res = client.get(
        _tasks_url(project.id),
        headers=_auth(owner),
        params={"status": "TODO", "page": 2, "size": 2},
    )

    body = res.json()
    assert [t["title"] for t in body["items"]] == ["todo2"]
    assert (body["total"], body["page"], body["size"]) == (3, 2, 2)


def test_list_bad_status_422(client, db):
    owner = make_user(db)
    project = make_project(db, owner)

    res = client.get(
        _tasks_url(project.id), headers=_auth(owner), params={"status": "DOING"}
    )

    assert res.status_code == 422


def test_list_non_member_403(client, team):
    res = client.get(_tasks_url(team["project_id"]), headers=_auth(team["outsider"]))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


# --- 상세 ---


def test_detail_200_for_member(client, team):
    res = client.get(_task_url(team["task_id"]), headers=_auth(team["other"]))

    assert res.status_code == 200
    assert res.json()["title"] == "원래 제목"


def test_detail_non_member_403(client, team):
    res = client.get(_task_url(team["task_id"]), headers=_auth(team["outsider"]))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_detail_not_found_404(client, db):
    res = client.get(_task_url(999_999), headers=_auth(make_user(db)))

    assert res.status_code == 404
    assert res.json() == {
        "code": "TASK_NOT_FOUND",
        "message": "업무를 찾을 수 없습니다",
    }


# --- 수정 (TASK-02·06, LOG-01·02) ---


def test_patch_status_and_assignee_two_activities(client, team, db):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["owner"]),
        json={"status": "IN_PROGRESS", "assignee_id": team["other"].id},
    )

    assert res.status_code == 200
    assert res.json()["assignee"]["id"] == team["other"].id
    got = [(r.field, r.old_value, r.new_value) for r in _activities(db)]
    assert got == [
        ("status", "TODO", "IN_PROGRESS"),
        ("assignee_id", str(team["assignee"].id), str(team["other"].id)),
    ]


def test_patch_done_sets_and_clears_completed_at(client, team):
    url, headers = _task_url(team["task_id"]), _auth(team["author"])

    done = client.patch(url, headers=headers, json={"status": "DONE"}).json()
    assert done["completed_at"].endswith("Z")

    todo = client.patch(url, headers=headers, json={"status": "TODO"}).json()
    assert todo["completed_at"] is None


def test_patch_null_title_422(client, team):
    res = client.patch(
        _task_url(team["task_id"]), headers=_auth(team["author"]), json={"title": None}
    )

    assert res.status_code == 422
    assert res.json()["errors"] == [
        {"field": "title", "message": "값을 비울 수 없습니다"}
    ]


def test_patch_bad_body_on_missing_task_422(client, db):
    """검사 순서 422 → 404 (API-SPEC §1.5)."""
    res = client.patch(
        _task_url(999_999), headers=_auth(make_user(db)), json={"title": ""}
    )

    assert res.status_code == 422


def test_patch_assignee_status_only_200(client, team):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["assignee"]),
        json={"status": "DONE"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "DONE"


def test_patch_assignee_other_field_403(client, team, db):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["assignee"]),
        json={"status": "DONE", "priority": "HIGH"},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
    db.rollback()
    assert db.get(Task, team["task_id"]).status == "TODO"
    assert _activities(db) == []


def test_patch_other_member_status_403(client, team):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["other"]),
        json={"status": "DONE"},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_patch_non_member_403(client, team):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["outsider"]),
        json={"status": "DONE"},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


# --- 삭제 (TASK-06) ---


def test_delete_204_keeps_activity(client, team, db):
    res = client.delete(_task_url(team["task_id"]), headers=_auth(team["author"]))

    assert res.status_code == 204
    assert res.content == b""
    [row] = _activities(db)
    assert (row.action, row.task_id, row.old_value) == ("DELETED", None, "원래 제목")
    assert db.get(Task, team["task_id"]) is None
    assert (
        client.get(_task_url(team["task_id"]), headers=_auth(team["owner"])).status_code
        == 404
    )


@pytest.mark.parametrize("who", ["assignee", "other"])
def test_delete_by_member_not_author_403(client, team, db, who):
    res = client.delete(_task_url(team["task_id"]), headers=_auth(team[who]))

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
    db.rollback()
    assert db.get(Task, team["task_id"]) is not None


def test_delete_without_token_401(client, team):
    assert client.delete(_task_url(team["task_id"])).status_code == 401


# --- 빈 PATCH (리뷰 보강: 권한표에 따른 {} 처리) ---


def test_patch_empty_body_by_assignee_200_no_change(client, team, db):
    """담당자의 {}는 'status만' 범위 안(빈 집합)이라 200, 바뀌는 것·이력 없음."""
    before = client.get(_task_url(team["task_id"]), headers=_auth(team["owner"])).json()

    res = client.patch(
        _task_url(team["task_id"]), headers=_auth(team["assignee"]), json={}
    )

    assert res.status_code == 200
    assert res.json() == before  # updated_at도 그대로
    assert _activities(db) == []


def test_patch_empty_body_by_other_member_403(client, team):
    """작성자도 담당자도 아닌 MEMBER는 {}여도 수정 권한이 없다."""
    res = client.patch(
        _task_url(team["task_id"]), headers=_auth(team["other"]), json={}
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


# --- 담당자 = 프로젝트 멤버 (T-F3-04, TASK-03, §10 "비멤버 담당자 400") ---

ASSIGNEE_ERROR = {
    "code": "ASSIGNEE_NOT_MEMBER",
    "message": "담당자는 프로젝트 멤버여야 합니다",
}


def test_create_non_member_assignee_400(client, team):
    res = client.post(
        _tasks_url(team["project_id"]),
        headers=_auth(team["owner"]),
        json={"title": "t", "assignee_id": team["outsider"].id},
    )

    assert res.status_code == 400
    assert res.json() == ASSIGNEE_ERROR


def test_patch_non_member_assignee_400(client, team):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["owner"]),
        json={"assignee_id": team["outsider"].id},
    )

    assert res.status_code == 400
    assert res.json() == ASSIGNEE_ERROR


def test_assignee_sends_assignee_id_403_not_400(client, team):
    """검사 순서 403 → 400 (API-SPEC §1.5): 권한이 없으면 담당자 검사까지 가지 않는다."""
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["assignee"]),
        json={"assignee_id": team["outsider"].id},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_non_member_create_with_non_member_assignee_403_not_400(client, team):
    """등록도 검사 순서 403 → 400: 비멤버는 담당자 검사 전에 NOT_PROJECT_MEMBER."""
    res = client.post(
        _tasks_url(team["project_id"]),
        headers=_auth(team["outsider"]),
        json={"title": "t", "assignee_id": team["outsider"].id},
    )

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


# --- description 최대 2000자 (API-SPEC v1.3, SPEC-CHANGELOG #15) ---


def test_create_description_2001_chars_422(client, team, db):
    """넘으면 500이 아니라 422 (예전에는 DB 한도 초과로 500)."""
    res = client.post(
        _tasks_url(team["project_id"]),
        headers=_auth(team["owner"]),
        json={"title": "t", "description": "가" * 2001},
    )

    assert res.status_code == 422
    assert res.json()["errors"] == [
        {"field": "description", "message": "2000자 이하로 입력해 주세요"}
    ]
    assert _activities(db) == []


def test_patch_description_2001_chars_422(client, team):
    res = client.patch(
        _task_url(team["task_id"]),
        headers=_auth(team["author"]),
        json={"description": "a" * 2001},
    )

    assert res.status_code == 422
    assert res.json()["errors"][0]["field"] == "description"
