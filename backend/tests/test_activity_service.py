"""이력 기록 함수 테스트 (T-F4-01, LOG-01·02).

근거: DATABASE-DESIGN §4.5, ARCHITECTURE §4.3.
- 이력 함수는 db.add()만 하고 커밋하지 않는다 → 테스트는 flush()로 확인한다.
- 대상 4개(status·assignee_id·due_date·priority)만, 바뀐 항목마다 1행.
- 값은 문자열("2", "2026-11-20"), 없음은 NULL.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TaskActivity
from app.models.enums import ActivityAction, TaskPriority, TaskStatus
from app.services import activity_service
from app.services.activity_service import record, record_changes, snapshot
from tests.factories import make_project, make_task, make_user


def _rows(db: Session) -> list[TaskActivity]:
    db.flush()
    return list(db.scalars(select(TaskActivity).order_by(TaskActivity.id)))


def _setup(db: Session, **task_fields):
    owner = make_user(db)
    project = make_project(db, owner)
    task = make_task(db, project, owner, **task_fields)
    return owner, project, task


def test_record_created_one_row(db: Session) -> None:
    owner, project, task = _setup(db)

    record(db, task, owner.id, ActivityAction.CREATED)

    rows = _rows(db)
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "CREATED"
    assert row.field is None
    assert row.old_value is None and row.new_value is None
    assert row.task_id == task.id
    assert row.project_id == project.id
    assert row.user_id == owner.id


def test_record_deleted_keeps_title(db: Session) -> None:
    owner, _, task = _setup(db, title="지울 업무")

    record(db, task, owner.id, ActivityAction.DELETED, old_value=task.title)

    [row] = _rows(db)
    assert row.action == "DELETED"
    assert row.field is None
    assert row.old_value == "지울 업무"


def test_record_changes_only_changed_fields(db: Session) -> None:
    owner, _, task = _setup(db)
    other = make_user(db)
    before = snapshot(task)

    task.status = TaskStatus.IN_PROGRESS
    task.assignee_id = other.id
    task.title = "새 제목"  # 제목은 이력 대상이 아니다
    count = record_changes(db, task, owner.id, before)

    assert count == 2
    rows = _rows(db)
    got = [(r.action, r.field, r.old_value, r.new_value) for r in rows]
    assert got == [
        ("UPDATED", "status", "TODO", "IN_PROGRESS"),
        ("UPDATED", "assignee_id", None, str(other.id)),
    ]


def test_record_changes_value_formats(db: Session) -> None:
    owner, _, task = _setup(db)
    task.assignee_id = owner.id
    db.commit()
    before = snapshot(task)

    task.due_date = date(2026, 11, 20)
    task.priority = TaskPriority.HIGH
    task.assignee_id = None
    count = record_changes(db, task, owner.id, before)

    assert count == 3
    got = {r.field: (r.old_value, r.new_value) for r in _rows(db)}
    assert got == {
        "assignee_id": (str(owner.id), None),
        "due_date": (None, "2026-11-20"),
        "priority": ("MEDIUM", "HIGH"),
    }


def test_record_changes_same_due_date_no_row(db: Session) -> None:
    owner, _, task = _setup(db, due_date=date(2026, 11, 20))
    before = snapshot(task)

    task.due_date = date(2026, 11, 20)  # 같은 날짜를 다시 넣음
    task.priority = TaskPriority.MEDIUM  # 같은 우선순위(기본값)를 다시 넣음
    count = record_changes(db, task, owner.id, before)

    assert count == 0
    assert _rows(db) == []


def test_record_does_not_commit(db: Session) -> None:
    owner, _, task = _setup(db)

    record(db, task, owner.id, ActivityAction.CREATED)
    db.rollback()  # 커밋하지 않았으므로 되돌리면 사라져야 한다

    assert _rows(db) == []


# --- task_title 규칙 (API-SPEC §6, SPEC-CHANGELOG #20). DB를 보지 않는 함수라 행 객체만 만든다 ---


def test_task_title_live_task_uses_titles() -> None:
    row = TaskActivity(task_id=1, action=ActivityAction.UPDATED, old_value="x")
    assert activity_service._task_title(row, {1: "제목"}) == "제목"


def test_task_title_deleted_row_uses_old_value() -> None:
    row = TaskActivity(task_id=None, action=ActivityAction.DELETED, old_value="삭제 전")
    assert activity_service._task_title(row, {}) == "삭제 전"


def test_task_title_deleted_task_other_row_none() -> None:
    row = TaskActivity(task_id=None, action=ActivityAction.UPDATED, old_value="TODO")
    assert activity_service._task_title(row, {}) is None


def test_task_title_live_task_wins_over_deleted_action() -> None:
    """업무가 있으면 action이 DELETED여도 지금 제목 — task_id 검사가 먼저다."""
    row = TaskActivity(task_id=1, action=ActivityAction.DELETED, old_value="옛 제목")
    assert activity_service._task_title(row, {1: "지금 제목"}) == "지금 제목"


def test_task_title_live_task_missing_from_titles_none() -> None:
    row = TaskActivity(task_id=2, action=ActivityAction.UPDATED, old_value="TODO")
    assert activity_service._task_title(row, {}) is None
