"""이력 기록 전수 테스트 (T-F4-02, LOG-01·02, API-SPEC §5.3 처리 2·§5.4 처리 1~4).

API로 이벤트를 일으키고 task_activities에 남는 행을 표처럼 확인한다.
| 이벤트 | 기대 행 |
| 등록 | CREATED 1 |
| 상태·담당자·마감일·우선순위 각각 변경(해제 포함) | UPDATED 1 (값은 문자열, 없음은 NULL) |
| 4개 동시 변경 | UPDATED 4 (status → assignee_id → due_date → priority) |
| 제목·설명만 / 같은 값 / 빈 본문 | 0 |
| 403·400·422로 거절된 수정 | 0 |
| 삭제 | DELETED 1(old_value = 제목), 그 업무 이력 전부 task_id NULL |
| 담당자 멤버 제거 | 담당 업무마다 UPDATED assignee_id "<id>" → NULL, 변경자 = 제거한 OWNER |

API가 쓴 데이터를 db 픽스처로 읽기 전에는 db.rollback()으로 트랜잭션을 끝낸다
(REPEATABLE READ라 열린 트랜잭션은 새 행을 못 본다).
"""

import pytest
from sqlalchemy import select

from app.models import TaskActivity
from core.security import create_access_token
from tests.factories import add_member, make_project, make_user


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _rows(db) -> list[tuple]:
    """(action, field, old_value, new_value) 목록, 기록 순서대로."""
    db.rollback()
    return [
        (r.action, r.field, r.old_value, r.new_value)
        for r in db.scalars(select(TaskActivity).order_by(TaskActivity.id))
    ]


def _updated(db) -> list[tuple]:
    """CREATED를 뺀 이력만."""
    return [r for r in _rows(db) if r[0] != "CREATED"]


@pytest.fixture
def ctx(client, db):
    """OWNER·작성자·담당자·그 외 MEMBER·비멤버 + 작성자가 API로 만든 업무 1개.

    업무 시작 값: TODO / MEDIUM / 담당자 assignee / 마감 2026-11-20 → 이력 CREATED 1행.
    """
    owner = make_user(db)
    project = make_project(db, owner)
    author, assignee, other, outsider = (make_user(db) for _ in range(4))
    for user in (author, assignee, other):
        add_member(db, project, user)
    res = client.post(
        f"/api/projects/{project.id}/tasks",
        headers=_auth(author),
        json={
            "title": "원래 제목",
            "assignee_id": assignee.id,
            "due_date": "2026-11-20",
        },
    )
    assert res.status_code == 201
    return {
        "client": client,
        "project_id": project.id,
        "task_id": res.json()["id"],
        "owner": owner,
        "author": author,
        "assignee": assignee,
        "other": other,
        "outsider": outsider,
    }


def _patch(ctx, user_key: str, body: dict):
    return ctx["client"].patch(
        f"/api/tasks/{ctx['task_id']}", headers=_auth(ctx[user_key]), json=body
    )


# --- 등록 ---


def test_create_records_one_created(ctx, db):
    assert _rows(db) == [("CREATED", None, None, None)]


# --- 항목 하나씩 변경 → UPDATED 1행 ---


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"status": "IN_PROGRESS"}, ("status", "TODO", "IN_PROGRESS")),
        ({"status": "DONE"}, ("status", "TODO", "DONE")),
        ({"assignee_id": "other"}, ("assignee_id", "assignee", "other")),
        ({"assignee_id": None}, ("assignee_id", "assignee", None)),
        ({"due_date": "2026-11-25"}, ("due_date", "2026-11-20", "2026-11-25")),
        ({"due_date": None}, ("due_date", "2026-11-20", None)),
        ({"priority": "URGENT"}, ("priority", "MEDIUM", "URGENT")),
    ],
    ids=[
        "status",
        "status-done",
        "assignee",
        "assignee-clear",
        "due",
        "due-clear",
        "priority",
    ],
)
def test_single_field_change_one_row(ctx, db, body, expected):
    def user_id(value):
        # 테스트 표에는 사람 이름 키를 쓰고, 실행할 때 실제 id로 바꾼다
        return str(ctx[value].id) if value in ("assignee", "other") else value

    if body.get("assignee_id") == "other":
        body = {"assignee_id": ctx["other"].id}
    field, old, new = expected

    res = _patch(ctx, "owner", body)

    assert res.status_code == 200
    assert _updated(db) == [("UPDATED", field, user_id(old), user_id(new))]


def test_all_four_changed_four_rows_in_order(ctx, db):
    res = _patch(
        ctx,
        "owner",
        {
            "priority": "LOW",
            "due_date": None,
            "assignee_id": ctx["other"].id,
            "status": "IN_PROGRESS",
        },
    )

    assert res.status_code == 200
    # 보낸 순서와 상관없이 status → assignee_id → due_date → priority
    assert _updated(db) == [
        ("UPDATED", "status", "TODO", "IN_PROGRESS"),
        ("UPDATED", "assignee_id", str(ctx["assignee"].id), str(ctx["other"].id)),
        ("UPDATED", "due_date", "2026-11-20", None),
        ("UPDATED", "priority", "MEDIUM", "LOW"),
    ]


# --- 이력이 남지 않는 경우 ---


@pytest.mark.parametrize(
    "body",
    [
        {"title": "새 제목", "description": "새 설명"},
        {"status": "TODO", "priority": "MEDIUM", "due_date": "2026-11-20"},
        {},
    ],
    ids=["title-description", "same-values", "empty"],
)
def test_no_row_when_nothing_tracked_changes(ctx, db, body):
    res = _patch(ctx, "owner", body)

    assert res.status_code == 200
    assert _updated(db) == []


def test_same_assignee_no_row(ctx, db):
    res = _patch(ctx, "owner", {"assignee_id": ctx["assignee"].id})

    assert res.status_code == 200
    assert _updated(db) == []


@pytest.mark.parametrize(
    ("user_key", "body", "status_code"),
    [
        ("other", {"status": "DONE"}, 403),  # 권한 없음
        ("assignee", {"status": "DONE", "priority": "HIGH"}, 403),  # 담당자 범위 밖
        ("owner", {"assignee_id": "outsider", "status": "DONE"}, 400),  # 비멤버 담당자
        ("owner", {"status": "DOING"}, 422),  # 입력 검증
    ],
    ids=["403-other", "403-assignee-scope", "400-assignee", "422"],
)
def test_rejected_update_no_row(ctx, db, user_key, body, status_code):
    if body.get("assignee_id") == "outsider":
        body = {**body, "assignee_id": ctx["outsider"].id}

    res = _patch(ctx, user_key, body)

    assert res.status_code == status_code
    assert _updated(db) == []


# --- 삭제 ---


def test_delete_records_deleted_and_keeps_history(ctx, db):
    _patch(ctx, "owner", {"status": "IN_PROGRESS"})  # UPDATED 1행을 먼저 쌓는다

    res = ctx["client"].delete(
        f"/api/tasks/{ctx['task_id']}", headers=_auth(ctx["author"])
    )

    assert res.status_code == 204
    assert _rows(db) == [
        ("CREATED", None, None, None),
        ("UPDATED", "status", "TODO", "IN_PROGRESS"),
        ("DELETED", None, "원래 제목", None),
    ]
    # 업무가 지워져도 이력은 모두 남고 task_id만 NULL (CONSTITUTION 8-3)
    assert all(
        r.task_id is None and r.project_id == ctx["project_id"]
        for r in db.scalars(select(TaskActivity))
    )


# --- 멤버 제거 → 담당 해제 이력 (PRJ-05, API-SPEC §5.3 처리 2) ---


def test_member_removal_unassigns_each_task_with_row(ctx, db):
    client, project_id = ctx["client"], ctx["project_id"]
    # 담당자에게 업무 하나를 더 맡기고, 다른 사람 담당 업무도 하나 만든다
    second = client.post(
        f"/api/projects/{project_id}/tasks",
        headers=_auth(ctx["owner"]),
        json={"title": "두 번째", "assignee_id": ctx["assignee"].id},
    ).json()
    untouched = client.post(
        f"/api/projects/{project_id}/tasks",
        headers=_auth(ctx["owner"]),
        json={"title": "남의 업무", "assignee_id": ctx["other"].id},
    ).json()
    before = len(_rows(db))

    res = client.delete(
        f"/api/projects/{project_id}/members/{ctx['assignee'].id}",
        headers=_auth(ctx["owner"]),
    )

    assert res.status_code == 204
    db.rollback()
    new_rows = list(
        db.scalars(select(TaskActivity).order_by(TaskActivity.id).offset(before))
    )
    assert [
        (r.task_id, r.action, r.field, r.old_value, r.new_value, r.user_id)
        for r in new_rows
    ] == [
        (
            task_id,
            "UPDATED",
            "assignee_id",
            str(ctx["assignee"].id),
            None,
            ctx["owner"].id,
        )
        for task_id in sorted([ctx["task_id"], second["id"]])
    ]
    assert untouched["id"] not in {r.task_id for r in new_rows}
