"""DB 규칙 테스트 — API 없이 DB에 직접 넣어 제약이 동작하는지 확인한다.

근거: DATABASE-DESIGN v1.1 §4·§7·§9. API를 통한 테스트(409·422 등)는 각 기능 테스트에서 한다.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.models import Task, TaskActivity, User
from app.models.enums import ActivityAction, TaskPriority, TaskStatus, priority_order
from tests.factories import DEFAULT_PASSWORD_HASH, make_project, make_task, make_user


def test_uppercase_login_id_rejected_by_db(db):
    """§9 아이디 소문자: DB에 대문자를 직접 INSERT하면 CHECK 오류 (utf8mb4_bin + REGEXP)."""
    db.add(User(login_id="MinHo", password_hash=DEFAULT_PASSWORD_HASH, name="민호"))
    with pytest.raises(DBAPIError, match="ck_users_login_id_format"):
        db.flush()


def test_updated_activity_without_field_rejected(db):
    """DATABASE-DESIGN v1.1 수정 회귀 테스트: UPDATED 이력에 field가 없으면 CHECK 오류."""
    owner = make_user(db)
    project = make_project(db, owner)
    task = make_task(db, project, owner)
    db.add(
        TaskActivity(
            task_id=task.id,
            project_id=project.id,
            user_id=owner.id,
            action=ActivityAction.UPDATED,
            field=None,
        )
    )
    with pytest.raises(DBAPIError, match="ck_task_activities_field"):
        db.flush()


def test_kanban_order_priority_then_due_date(db):
    """§9 칸반 정렬(TASK-05): 우선순위 높은 순 → 마감일 빠른 순(없음은 뒤) → id."""
    owner = make_user(db)
    project = make_project(db, owner)
    # 일부러 섞인 순서로 만든다
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

    titles = db.scalars(
        select(Task.title)
        .where(Task.project_id == project.id, Task.status == TaskStatus.TODO)
        .order_by(
            priority_order(Task.priority),
            Task.due_date.is_(None),
            Task.due_date,
            Task.id,
        )
    ).all()

    assert titles == [
        "urgent",
        "high-early",
        "high-late",
        "high-none",
        "medium",
        "low",
    ]
