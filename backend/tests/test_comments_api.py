"""댓글 API 테스트 (T-F4-03, CMT-01·02, API-SPEC §6 "댓글").

- GET·POST /api/tasks/{task_id}/comments: 멤버 누구나. 목록은 오래된 순(created_at, id).
- PATCH·DELETE /api/comments/{comment_id}: 작성자만. OWNER도 남의 댓글은 403 FORBIDDEN.
- 내용: 앞뒤 공백 제거 후 1~300자(빈 댓글·초과 422).
- 검사 순서(§1.5): 401 → 422 → 404 → 403 NOT_PROJECT_MEMBER → 403 FORBIDDEN.
- Comment: { id, task_id, user: UserBrief, content, created_at, updated_at }
  화면은 updated_at이 created_at과 다르면 "수정됨"을 표시한다(CMT-02).
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import event, func, select, update

from app.models import Project, TaskComment
from tests.factories import add_member, make_project, make_task, make_user
from tests.factories import auth_header as _auth

PAST = datetime(2026, 11, 20, 1, 0, 0)  # UTC, 작성 시각을 직접 정할 때


def _brief(user) -> dict:
    return {"id": user.id, "login_id": user.login_id, "name": user.name}


def _list_url(task_id: int) -> str:
    return f"/api/tasks/{task_id}/comments"


def _one_url(comment_id: int) -> str:
    return f"/api/comments/{comment_id}"


@pytest.fixture
def team(db):
    """OWNER 지수, MEMBER 민호·서연, 비멤버, 업무 1개."""
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    minho = make_user(db, name="민호")
    seoyeon = make_user(db, name="서연")
    add_member(db, project, minho)
    add_member(db, project, seoyeon)
    task = make_task(db, project, owner)
    return {
        "owner": owner,
        "minho": minho,
        "seoyeon": seoyeon,
        "outsider": make_user(db),
        "project_id": project.id,
        "task_id": task.id,
    }


def _write(client, team, user, content="댓글") -> dict:
    res = client.post(
        _list_url(team["task_id"]), headers=_auth(user), json={"content": content}
    )
    assert res.status_code == 201, res.text
    return res.json()


def _list(client, team, user=None, **params) -> dict:
    res = client.get(
        _list_url(team["task_id"]),
        headers=_auth(user or team["owner"]),
        params=params,
    )
    assert res.status_code == 200, res.text
    return res.json()


def _set_created_at(db, values: dict[int, datetime]) -> None:
    for comment_id, created_at in values.items():
        db.execute(
            update(TaskComment)
            .where(TaskComment.id == comment_id)
            .values(created_at=created_at, updated_at=created_at)
        )
    db.commit()


# --- 작성·조회 (CMT-01) ---


def test_create_and_list_oldest_first(client, team):
    """CMT-01-a: 작성자·시각과 함께 오래된 순 목록 맨 아래에 보인다."""
    first = _write(client, team, team["minho"], "첫 댓글")
    second = _write(client, team, team["owner"], "둘째 댓글")

    body = _list(client, team, team["seoyeon"])

    assert set(second) == {
        "id",
        "task_id",
        "user",
        "content",
        "created_at",
        "updated_at",
    }
    assert second["task_id"] == team["task_id"]
    assert second["user"] == _brief(team["owner"])
    assert second["created_at"].endswith("Z") and second["updated_at"].endswith("Z")
    assert [i["id"] for i in body["items"]] == [first["id"], second["id"]]
    assert [i["user"]["name"] for i in body["items"]] == ["민호", "지수"]
    assert body["total"] == 2 and body["page"] == 1 and body["size"] == 20


def test_list_order_created_at_then_id(client, team, db):
    """시각이 먼저, 같은 시각이면 id 순 (DATABASE-DESIGN §7: created_at, id)."""
    a = _write(client, team, team["owner"], "a")["id"]
    b = _write(client, team, team["owner"], "b")["id"]
    c = _write(client, team, team["owner"], "c")["id"]
    # a는 늦게, b·c는 같은 시각
    _set_created_at(db, {a: PAST + timedelta(minutes=5), b: PAST, c: PAST})

    ids = [i["id"] for i in _list(client, team)["items"]]

    assert ids == [b, c, a]


def test_content_trimmed_and_300_chars_ok(client, team):
    trimmed = _write(client, team, team["owner"], "  앞뒤 공백  ")
    exact = _write(client, team, team["owner"], "가" * 300)
    emoji = _write(client, team, team["owner"], "😀" * 300)

    assert trimmed["content"] == "앞뒤 공백"
    assert len(exact["content"]) == 300
    assert emoji["content"] == "😀" * 300


@pytest.mark.parametrize("content", ["", "   ", "가" * 301])
def test_bad_content_422(client, team, content):
    """CMT-01-b: 비어 있거나 300자를 넘으면 등록되지 않는다."""
    res = client.post(
        _list_url(team["task_id"]),
        headers=_auth(team["owner"]),
        json={"content": content},
    )

    assert res.status_code == 422
    assert res.json()["errors"][0]["field"] == "content"
    assert _list(client, team)["total"] == 0


# --- 수정·삭제 (CMT-02) ---


def test_owner_cannot_edit_or_delete_others_comment(client, team):
    """CMT-02-a: OWNER라도 남의 댓글은 수정·삭제할 수 없다."""
    comment = _write(client, team, team["minho"], "민호 댓글")

    patch = client.patch(
        _one_url(comment["id"]), headers=_auth(team["owner"]), json={"content": "x"}
    )
    delete = client.delete(_one_url(comment["id"]), headers=_auth(team["owner"]))

    assert patch.status_code == 403 and patch.json()["code"] == "FORBIDDEN"
    assert delete.status_code == 403 and delete.json()["code"] == "FORBIDDEN"
    assert [i["content"] for i in _list(client, team)["items"]] == ["민호 댓글"]


def test_other_member_cannot_edit_comment(client, team):
    comment = _write(client, team, team["minho"])

    res = client.patch(
        _one_url(comment["id"]), headers=_auth(team["seoyeon"]), json={"content": "x"}
    )

    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN"


def test_author_edit_updates_updated_at(client, team, db):
    """수정하면 updated_at이 바뀌어 화면이 "수정됨"을 표시한다 (CMT-02)."""
    comment = _write(client, team, team["minho"], "처음")
    _set_created_at(db, {comment["id"]: PAST})

    res = client.patch(
        _one_url(comment["id"]),
        headers=_auth(team["minho"]),
        json={"content": "  고친 내용  "},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "고친 내용"
    assert body["created_at"] == "2026-11-20T01:00:00Z"
    assert body["updated_at"] > body["created_at"]
    assert _list(client, team)["items"][0]["content"] == "고친 내용"


@pytest.mark.parametrize("content", ["   ", "가" * 301])
def test_edit_bad_content_422_and_unchanged(client, team, content):
    comment = _write(client, team, team["minho"], "그대로")

    res = client.patch(
        _one_url(comment["id"]),
        headers=_auth(team["minho"]),
        json={"content": content},
    )

    assert res.status_code == 422
    assert _list(client, team)["items"][0]["content"] == "그대로"


def test_author_delete_then_404(client, team):
    comment = _write(client, team, team["minho"])

    res = client.delete(_one_url(comment["id"]), headers=_auth(team["minho"]))
    again = client.delete(_one_url(comment["id"]), headers=_auth(team["minho"]))

    assert res.status_code == 204 and res.content == b""
    assert again.status_code == 404 and again.json()["code"] == "COMMENT_NOT_FOUND"
    assert _list(client, team)["total"] == 0


def test_removed_member_comment(client, team):
    """멤버에서 제거된 작성자는 자기 댓글도 못 고치고(403), 목록에는 이름이 남는다."""
    comment = _write(client, team, team["minho"], "남는 댓글")
    res = client.delete(
        f"/api/projects/{team['project_id']}/members/{team['minho'].id}",
        headers=_auth(team["owner"]),
    )
    assert res.status_code == 204

    patch = client.patch(
        _one_url(comment["id"]), headers=_auth(team["minho"]), json={"content": "x"}
    )

    assert patch.status_code == 403 and patch.json()["code"] == "NOT_PROJECT_MEMBER"
    assert _list(client, team)["items"][0]["user"] == _brief(team["minho"])


def test_task_delete_removes_comments(client, team, db):
    _write(client, team, team["minho"])

    res = client.delete(f"/api/tasks/{team['task_id']}", headers=_auth(team["owner"]))

    assert res.status_code == 204
    assert db.scalar(select(func.count()).select_from(TaskComment)) == 0


# --- 권한·검사 순서 (§1.5) ---


def test_comment_permissions_order(client, team):
    comment = _write(client, team, team["minho"])
    outsider = _auth(team["outsider"])
    task_url, one_url = _list_url(team["task_id"]), _one_url(comment["id"])

    # 401
    assert client.get(task_url).status_code == 401
    assert client.patch(one_url, json={"content": "x"}).status_code == 401
    # 비멤버 403 (목록·작성·수정·삭제)
    for res in (
        client.get(task_url, headers=outsider),
        client.post(task_url, headers=outsider, json={"content": "x"}),
        client.patch(one_url, headers=outsider, json={"content": "x"}),
        client.delete(one_url, headers=outsider),
    ):
        assert res.status_code == 403 and res.json()["code"] == "NOT_PROJECT_MEMBER"
    # 없는 업무·댓글은 비멤버에게도 404 (403보다 먼저)
    missing_task = client.get(_list_url(999_999), headers=outsider)
    missing_comment = client.patch(
        _one_url(999_999), headers=outsider, json={"content": "x"}
    )
    assert missing_task.json()["code"] == "TASK_NOT_FOUND"
    assert missing_comment.json()["code"] == "COMMENT_NOT_FOUND"
    # 잘못된 본문은 422가 404·403보다 먼저
    assert client.post(task_url, headers=outsider, json={}).status_code == 422
    assert (
        client.patch(_one_url(999_999), headers=outsider, json={"content": ""})
    ).status_code == 422


def test_comment_paging_and_size_limit(client, team):
    ids = [_write(client, team, team["owner"], f"{i}")["id"] for i in range(3)]

    page2 = _list(client, team, page=2, size=2)
    too_big = client.get(
        _list_url(team["task_id"]), headers=_auth(team["owner"]), params={"size": 101}
    )

    assert [i["id"] for i in page2["items"]] == ids[2:]
    assert page2["total"] == 3 and page2["size"] == 2
    assert too_big.status_code == 422


def test_comments_start_empty_each_test(db):
    """앞 테스트의 댓글이 남지 않는다(모델 등록 → conftest TRUNCATE 대상)."""
    assert db.scalar(select(func.count()).select_from(TaskComment)) == 0


# --- 쿼리 수 (N+1 방지) ---


def _count_queries(engine, func_) -> int:
    statements: list[str] = []

    def _before(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        func_()
    finally:
        event.remove(engine, "before_cursor_execute", _before)
    return len(statements)


def test_comment_list_query_count_constant(client, team, db, engine):
    """작성자가 모두 달라도 목록 요청 1번의 SQL 수는 같다."""

    def _add_writers(count: int) -> None:
        for _ in range(count):
            person = make_user(db)
            add_member(db, db.get(Project, team["project_id"]), person)
            _write(client, team, person)

    _add_writers(1)
    small = _count_queries(engine, lambda: _list(client, team))
    _add_writers(9)
    large = _count_queries(engine, lambda: _list(client, team))

    assert _list(client, team)["total"] == 10
    assert large == small
