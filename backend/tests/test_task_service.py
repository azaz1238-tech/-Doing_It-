"""업무 서비스 테스트 (T-F2-07~09, TASK-01~06, LOG-01·02).

서비스는 로그인 사용자(User)와 id를 받아, 안에서 조회(404)와 권한(403)을 검사한다
(ARCHITECTURE §4.2, 팀장 project_service와 같은 모양).
"""

from dataclasses import dataclass
from datetime import date, datetime

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Project, Task, TaskActivity, User
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import activity_service
from app.services.task_service import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)
from core.exceptions import Forbidden, NotFound
from core.pagination import PageParams
from tests.factories import add_member, make_project, make_task, make_user


def _activities(db: Session) -> list[TaskActivity]:
    return list(db.scalars(select(TaskActivity).order_by(TaskActivity.id)))


# ---------- 등록 (TASK-01) ----------


def test_create_task_records_created(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)

    task = create_task(
        db,
        owner,
        project.id,
        TaskCreate(title="로그인 API", priority=TaskPriority.HIGH),
    )

    assert task.id is not None
    assert task.project_id == project.id
    assert task.created_by == owner.id
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH
    assert task.completed_at is None
    [row] = _activities(db)
    assert (row.action, row.field, row.task_id) == ("CREATED", None, task.id)
    assert row.user_id == owner.id


def test_create_task_commits(db: Session, engine: Engine) -> None:
    owner = make_user(db)
    project = make_project(db, owner)

    task = create_task(db, owner, project.id, TaskCreate(title="t"))

    # 다른 세션에서도 보이면 커밋된 것
    other = sessionmaker(bind=engine)()
    try:
        assert other.get(Task, task.id) is not None
        assert len(list(other.scalars(select(TaskActivity)))) == 1
    finally:
        other.close()


def test_create_task_project_not_found(db: Session) -> None:
    with pytest.raises(NotFound) as exc:
        create_task(db, make_user(db), 999_999, TaskCreate(title="t"))
    assert exc.value.code == "PROJECT_NOT_FOUND"


def test_create_task_non_member_forbidden(db: Session) -> None:
    project = make_project(db, make_user(db))

    with pytest.raises(Forbidden) as exc:
        create_task(db, make_user(db), project.id, TaskCreate(title="t"))

    assert exc.value.code == "NOT_PROJECT_MEMBER"
    db.rollback()
    assert _activities(db) == []


# ---------- 칸반 목록 (TASK-05) ----------


def test_list_tasks_kanban_order(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    specs = [
        ("low", TaskPriority.LOW, None),
        ("high-none", TaskPriority.HIGH, None),
        ("urgent", TaskPriority.URGENT, date(2026, 11, 30)),
        ("high-late", TaskPriority.HIGH, date(2026, 11, 25)),
        ("medium", TaskPriority.MEDIUM, date(2026, 11, 17)),
        ("high-early", TaskPriority.HIGH, date(2026, 11, 20)),
    ]
    for title, priority, due in specs:
        make_task(db, project, owner, title=title, priority=priority, due_date=due)

    items, total = list_tasks(db, owner, project.id, None, PageParams())

    assert total == 6
    assert [t.title for t in items] == [
        "urgent",
        "high-early",
        "high-late",
        "high-none",
        "medium",
        "low",
    ]


def test_list_tasks_filters_status_and_project(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    other_project = make_project(db, owner)
    make_task(db, project, owner, title="todo")
    make_task(db, project, owner, title="done", status=TaskStatus.DONE)
    make_task(db, other_project, owner, title="other")

    items, total = list_tasks(db, owner, project.id, TaskStatus.TODO, PageParams())
    assert ([t.title for t in items], total) == (["todo"], 1)

    items, total = list_tasks(db, owner, project.id, None, PageParams())
    assert (sorted(t.title for t in items), total) == (["done", "todo"], 2)


def test_list_tasks_pagination(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    for i in range(5):
        make_task(db, project, owner, title=f"t{i}")

    items, total = list_tasks(db, owner, project.id, None, PageParams(page=2, size=2))

    # 같은 우선순위·마감일 없음 → id 순 → 2페이지는 t2, t3
    assert [t.title for t in items] == ["t2", "t3"]
    assert total == 5


def test_list_tasks_page_beyond_total(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    for i in range(5):
        make_task(db, project, owner, title=f"t{i}")

    items, total = list_tasks(db, owner, project.id, None, PageParams(page=10, size=20))

    assert items == []
    assert total == 5


def test_list_tasks_loads_users(db: Session) -> None:
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    make_task(db, project, owner, assignee_id=owner.id)

    [task], _ = list_tasks(db, owner, project.id, None, PageParams())

    assert task.creator.name == "지수"
    assert task.assignee is not None and task.assignee.id == owner.id


# ---------- 조회 ----------


def test_get_task_for_member(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    task = make_task(db, project, owner)

    assert get_task(db, owner, task.id).id == task.id


def test_get_task_not_found(db: Session) -> None:
    with pytest.raises(NotFound) as exc:
        get_task(db, make_user(db), 999_999)
    assert exc.value.code == "TASK_NOT_FOUND"
    assert exc.value.message == "업무를 찾을 수 없습니다"


def test_get_task_non_member_forbidden(db: Session) -> None:
    owner = make_user(db)
    task = make_task(db, make_project(db, owner), owner)

    with pytest.raises(Forbidden) as exc:
        get_task(db, make_user(db), task.id)
    assert exc.value.code == "NOT_PROJECT_MEMBER"


def test_list_tasks_non_member_forbidden(db: Session) -> None:
    project = make_project(db, make_user(db))

    with pytest.raises(Forbidden) as exc:
        list_tasks(db, make_user(db), project.id, None, PageParams())
    assert exc.value.code == "NOT_PROJECT_MEMBER"


# ---------- 수정 (TASK-02·06, LOG-01·02) ----------


@dataclass
class Cast:
    """권한 테스트 등장인물. 업무는 author가 만들고 assignee가 담당한다."""

    project: Project
    owner: User  # OWNER
    author: User  # MEMBER + 작성자
    assignee: User  # MEMBER + 담당자(작성자 아님)
    other: User  # 그 외 MEMBER
    task: Task


@pytest.fixture
def cast(db: Session) -> Cast:
    owner = make_user(db)
    project = make_project(db, owner)
    author, assignee, other = make_user(db), make_user(db), make_user(db)
    for user in (author, assignee, other):
        add_member(db, project, user)
    task = make_task(db, project, author, title="원래 제목", assignee_id=assignee.id)
    return Cast(project, owner, author, assignee, other, task)


def _update(db: Session, cast: Cast, user: User, body: dict) -> Task:
    return update_task(db, user, cast.task.id, TaskUpdate.model_validate(body))


def _snapshot_row(db: Session, task_id: int) -> tuple:
    """다른 세션에서 읽은 업무 값(커밋된 값)."""
    other = sessionmaker(bind=db.get_bind())()
    try:
        t = other.get(Task, task_id)
        return (t.title, t.status, t.priority, t.assignee_id, t.due_date)
    finally:
        other.close()


def test_update_status_and_assignee_two_rows(db: Session, cast: Cast) -> None:
    _update(
        db,
        cast,
        cast.owner,
        {"status": "IN_PROGRESS", "assignee_id": cast.other.id},
    )

    got = [(r.field, r.old_value, r.new_value) for r in _activities(db)]
    assert got == [
        ("status", "TODO", "IN_PROGRESS"),
        ("assignee_id", str(cast.assignee.id), str(cast.other.id)),
    ]
    assert all(r.action == "UPDATED" for r in _activities(db))
    assert all(r.user_id == cast.owner.id for r in _activities(db))


def test_update_title_description_no_row(db: Session, cast: Cast) -> None:
    task = _update(db, cast, cast.author, {"title": "새 제목", "description": "설명"})

    assert (task.title, task.description) == ("새 제목", "설명")
    assert _activities(db) == []


def test_update_empty_body_no_change(db: Session, cast: Cast) -> None:
    before = _snapshot_row(db, cast.task.id)

    _update(db, cast, cast.author, {})

    assert _snapshot_row(db, cast.task.id) == before
    assert _activities(db) == []


def test_update_done_sets_and_clears_completed_at(db: Session, cast: Cast) -> None:
    task = _update(db, cast, cast.author, {"status": "DONE"})
    assert task.completed_at is not None

    task = _update(db, cast, cast.author, {"status": "TODO"})
    assert task.completed_at is None


def test_update_done_to_done_keeps_completed_at(db: Session, cast: Cast) -> None:
    done_at = datetime(2026, 11, 15, 3, 0, 0)
    cast.task.status = TaskStatus.DONE
    cast.task.completed_at = done_at
    db.commit()

    task = _update(db, cast, cast.author, {"status": "DONE"})

    assert task.completed_at == done_at
    assert _activities(db) == []


def test_update_is_committed(db: Session, cast: Cast) -> None:
    _update(db, cast, cast.author, {"priority": "URGENT"})

    assert _snapshot_row(db, cast.task.id)[2] == "URGENT"


# ---------- 수정 권한 (TASK-06 권한 매트릭스) ----------


def test_owner_can_edit_any(db: Session, cast: Cast) -> None:
    task = _update(db, cast, cast.owner, {"title": "OWNER 수정", "priority": "LOW"})
    assert (task.title, task.priority) == ("OWNER 수정", "LOW")


def test_author_can_edit_all_fields(db: Session, cast: Cast) -> None:
    body = {
        "title": "작성자 수정",
        "description": "d",
        "status": "IN_PROGRESS",
        "assignee_id": None,
        "due_date": "2026-11-20",
        "priority": "HIGH",
    }
    task = _update(db, cast, cast.author, body)

    assert task.title == "작성자 수정"
    assert task.assignee_id is None
    assert task.due_date == date(2026, 11, 20)


def test_assignee_can_change_status(db: Session, cast: Cast) -> None:
    task = _update(db, cast, cast.assignee, {"status": "DONE"})
    assert task.status == TaskStatus.DONE


def test_assignee_other_field_forbidden(db: Session, cast: Cast) -> None:
    before = _snapshot_row(db, cast.task.id)

    with pytest.raises(Forbidden) as exc:
        _update(db, cast, cast.assignee, {"status": "DONE", "priority": "HIGH"})

    assert exc.value.code == "FORBIDDEN"
    db.rollback()
    assert _snapshot_row(db, cast.task.id) == before  # status도 안 바뀜(요청 전체 거절)
    assert _activities(db) == []


def test_author_who_is_assignee_can_edit_all(db: Session, cast: Cast) -> None:
    cast.task.assignee_id = cast.author.id
    db.commit()

    task = _update(db, cast, cast.author, {"title": "둘 다", "priority": "LOW"})

    assert (task.title, task.priority) == ("둘 다", "LOW")


def test_other_member_forbidden(db: Session, cast: Cast) -> None:
    before = _snapshot_row(db, cast.task.id)

    with pytest.raises(Forbidden):
        _update(db, cast, cast.other, {"status": "DONE"})

    db.rollback()
    assert _snapshot_row(db, cast.task.id) == before
    assert _activities(db) == []


# ---------- 삭제 (TASK-06, LOG-01) ----------


def test_delete_keeps_activity_with_null_task_id(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    task = create_task(
        db, owner, project.id, TaskCreate(title="지울 업무")
    )  # CREATED 1행
    task_id = task.id

    delete_task(db, owner, task_id)

    db.expire_all()
    assert db.get(Task, task_id) is None
    rows = _activities(db)
    assert [(r.action, r.task_id) for r in rows] == [
        ("CREATED", None),
        ("DELETED", None),
    ]
    assert rows[1].old_value == "지울 업무"
    assert rows[1].field is None
    assert rows[1].user_id == owner.id
    assert rows[1].project_id == project.id


@pytest.mark.parametrize("who", ["owner", "author"])
def test_delete_by_owner_and_author_ok(db: Session, cast: Cast, who: str) -> None:
    task_id = cast.task.id

    delete_task(db, getattr(cast, who), task_id)

    db.expire_all()
    assert db.get(Task, task_id) is None


@pytest.mark.parametrize("who", ["assignee", "other"])
def test_delete_by_other_member_forbidden(db: Session, cast: Cast, who: str) -> None:
    with pytest.raises(Forbidden):
        delete_task(db, getattr(cast, who), cast.task.id)

    db.rollback()
    assert _snapshot_row(db, cast.task.id)[0] == "원래 제목"
    assert _activities(db) == []


# ---------- 한 트랜잭션 (API-SPEC §5.4 처리 4) ----------


def test_update_rolls_back_when_activity_fails(
    db: Session, cast: Cast, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _snapshot_row(db, cast.task.id)

    def broken_record(*args, **kwargs):
        raise RuntimeError("이력 기록 실패")

    monkeypatch.setattr(activity_service, "record", broken_record)

    with pytest.raises(RuntimeError):
        _update(db, cast, cast.author, {"status": "DONE", "priority": "HIGH"})

    db.rollback()  # 실제로는 get_db가 한다
    assert _snapshot_row(db, cast.task.id) == before


def test_delete_rolls_back_when_activity_fails(
    db: Session, cast: Cast, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_record(*args, **kwargs):
        raise RuntimeError("이력 기록 실패")

    monkeypatch.setattr(activity_service, "record", broken_record)

    with pytest.raises(RuntimeError):
        delete_task(db, cast.owner, cast.task.id)

    db.rollback()
    assert _snapshot_row(db, cast.task.id)[0] == "원래 제목"
