"""업무 서비스 테스트 (T-F2-07~09, TASK-01~06, LOG-01·02).

서비스는 라우터가 require_project_role()로 얻은 ProjectMember를 받는다.
테스트에서는 factories.member_of()로 같은 객체를 만든다.
"""

from datetime import date

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Task, TaskActivity
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate
from app.services.task_service import create_task, get_task_or_404, list_tasks
from core.exceptions import NotFound
from core.pagination import PageParams
from tests.factories import make_project, make_task, make_user, member_of


def _activities(db: Session) -> list[TaskActivity]:
    return list(db.scalars(select(TaskActivity).order_by(TaskActivity.id)))


# ---------- 등록 (TASK-01) ----------


def test_create_task_records_created(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    member = member_of(db, project, owner)

    task = create_task(
        db, member, TaskCreate(title="로그인 API", priority=TaskPriority.HIGH)
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

    task = create_task(db, member_of(db, project, owner), TaskCreate(title="t"))

    # 다른 세션에서도 보이면 커밋된 것
    other = sessionmaker(bind=engine)()
    try:
        assert other.get(Task, task.id) is not None
        assert len(list(other.scalars(select(TaskActivity)))) == 1
    finally:
        other.close()


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

    items, total = list_tasks(db, project.id, None, PageParams())

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

    items, total = list_tasks(db, project.id, TaskStatus.TODO, PageParams())
    assert ([t.title for t in items], total) == (["todo"], 1)

    items, total = list_tasks(db, project.id, None, PageParams())
    assert (sorted(t.title for t in items), total) == (["done", "todo"], 2)


def test_list_tasks_pagination(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    for i in range(5):
        make_task(db, project, owner, title=f"t{i}")

    items, total = list_tasks(db, project.id, None, PageParams(page=2, size=2))

    # 같은 우선순위·마감일 없음 → id 순 → 2페이지는 t2, t3
    assert [t.title for t in items] == ["t2", "t3"]
    assert total == 5


def test_list_tasks_page_beyond_total(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    for i in range(5):
        make_task(db, project, owner, title=f"t{i}")

    items, total = list_tasks(db, project.id, None, PageParams(page=10, size=20))

    assert items == []
    assert total == 5


def test_list_tasks_loads_users(db: Session) -> None:
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    make_task(db, project, owner, assignee_id=owner.id)

    [task], _ = list_tasks(db, project.id, None, PageParams())

    assert task.creator.name == "지수"
    assert task.assignee is not None and task.assignee.id == owner.id


# ---------- 조회 ----------


def test_get_task_or_404(db: Session) -> None:
    owner = make_user(db)
    project = make_project(db, owner)
    task = make_task(db, project, owner)

    assert get_task_or_404(db, task.id).id == task.id
    with pytest.raises(NotFound) as exc:
        get_task_or_404(db, 999_999)
    assert exc.value.code == "TASK_NOT_FOUND"
    assert exc.value.message == "업무를 찾을 수 없습니다"
