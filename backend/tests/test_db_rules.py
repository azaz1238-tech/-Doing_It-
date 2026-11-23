"""DB 규칙 테스트 — API 없이 DB에 직접 넣어 제약이 동작하는지 확인한다.

근거: DATABASE-DESIGN v1.4 §4·§7·§8.1·§9. API를 통한 테스트(409·422 등)는 각 기능 테스트에서 한다.
"""

from datetime import date

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError

from app.models import ProjectMember, Task, TaskActivity, TaskComment, User
from app.models.enums import ActivityAction, TaskPriority, TaskStatus, priority_order
from tests.factories import DEFAULT_PASSWORD_HASH, make_project, make_task, make_user


@pytest.mark.parametrize(
    ("kind", "value", "constraint"),
    [
        ("task_status", "todo", "ck_tasks_status"),
        ("task_priority", "high", "ck_tasks_priority"),
        ("member_role", "owner", "ck_project_members_role"),
        ("system_role", "user", "ck_users_system_role"),
        # 'created'는 action CHECK와 field CHECK를 둘 다 위반 → MariaDB가 어느 쪽을 먼저 보고할지 정하지 않는다
        ("activity_action", "created", "ck_task_activities_(action|field)"),
        ("activity_field", "Status", "ck_task_activities_field"),
    ],
)
def test_enum_columns_are_case_sensitive(db, kind, value, constraint):
    """상태·역할 값은 대문자 enum 값만 저장된다 (utf8mb4_bin, CONSTITUTION 8-4).

    기본 _ci 콜레이션이면 'todo'가 'TODO'와 같다고 보고 CHECK를 통과한다.
    """
    owner = make_user(db)
    project = make_project(db, owner)
    task = make_task(db, project, owner)
    other = make_user(db)
    rows = {
        "task_status": Task(
            project_id=project.id, created_by=owner.id, title="t", status=value
        ),
        "task_priority": Task(
            project_id=project.id, created_by=owner.id, title="t", priority=value
        ),
        "member_role": ProjectMember(
            project_id=project.id, user_id=other.id, role=value
        ),
        "system_role": User(
            login_id="lower1",
            password_hash=DEFAULT_PASSWORD_HASH,
            name="n",
            system_role=value,
        ),
        "activity_action": TaskActivity(
            task_id=task.id, project_id=project.id, user_id=owner.id, action=value
        ),
        "activity_field": TaskActivity(
            task_id=task.id,
            project_id=project.id,
            user_id=owner.id,
            action=ActivityAction.UPDATED,
            field=value,
        ),
    }
    db.add(rows[kind])
    with pytest.raises(DBAPIError, match=constraint):
        db.flush()


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


def test_comment_blank_content_rejected_by_check(db):
    """§4.6 댓글: 공백만 있는 내용은 앱 검증을 건너뛰어도 DB CHECK가 막는다 (CMT-01)."""
    owner = make_user(db)
    task = make_task(db, make_project(db, owner), owner)
    db.add(TaskComment(task_id=task.id, user_id=owner.id, content="   "))
    with pytest.raises(DBAPIError, match="ck_task_comments_content_not_blank"):
        db.flush()


def test_task_delete_cascades_comments(db):
    """§5 업무를 지우면 댓글도 DB CASCADE로 지워진다."""
    owner = make_user(db)
    task = make_task(db, make_project(db, owner), owner)
    db.add(TaskComment(task_id=task.id, user_id=owner.id, content="댓글"))
    db.commit()

    db.execute(delete(Task).where(Task.id == task.id))
    db.commit()

    assert db.scalar(select(func.count()).select_from(TaskComment)) == 0


def test_p1_indexes_exist(db):
    """§8.1 P1 인덱스가 리비전 0003으로 만들어졌는지 (SPEC-CHANGELOG #24)."""
    rows = db.execute(
        text(
            "SELECT TABLE_NAME, INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX)"
            " FROM information_schema.STATISTICS"
            " WHERE TABLE_SCHEMA = DATABASE()"
            " AND INDEX_NAME IN ('ix_tasks_project_due', 'ix_task_comments_task')"
            " GROUP BY TABLE_NAME, INDEX_NAME"
        )
    ).all()

    assert sorted(tuple(r) for r in rows) == [
        ("task_comments", "ix_task_comments_task", "task_id,created_at"),
        ("tasks", "ix_tasks_project_due", "project_id,due_date"),
    ]


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
