"""업무 요청·응답 스키마 테스트 (T-F2-07~09, API-SPEC §4·§5.4).

- 등록: title 필수(앞뒤 공백 제거 후 1~30자), status는 받지 않음, priority 기본 MEDIUM
- 수정: 보낸 필드만 반영(model_fields_set). title·priority·status는 null 불가,
  assignee_id·due_date·description은 null로 해제 가능
- 응답: Task 객체 모양(created_by·assignee는 UserBrief, 시각은 Z)
"""

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from tests.factories import make_project, make_task, make_user


def test_create_title_strip_and_limits() -> None:
    assert TaskCreate(title="  a  ").title == "a"
    assert TaskCreate(title="가" * 30).title == "가" * 30
    with pytest.raises(ValidationError):
        TaskCreate(title="가" * 31)
    with pytest.raises(ValidationError):
        TaskCreate(title="   ")


def test_create_rejects_status() -> None:
    with pytest.raises(ValidationError) as exc:
        TaskCreate.model_validate({"title": "t", "status": "DONE"})
    assert exc.value.errors()[0]["type"] == "extra_forbidden"


def test_create_default_priority_medium() -> None:
    data = TaskCreate(title="t")
    assert data.priority == TaskPriority.MEDIUM
    assert data.assignee_id is None and data.due_date is None


def test_update_fields_set_only_sent() -> None:
    data = TaskUpdate.model_validate({"status": "DONE"})
    assert data.model_fields_set == {"status"}
    assert data.status == TaskStatus.DONE
    assert TaskUpdate.model_validate({}).model_fields_set == set()


@pytest.mark.parametrize("field", ["title", "priority", "status"])
def test_update_null_not_allowed_fields_rejected(field: str) -> None:
    with pytest.raises(ValidationError) as exc:
        TaskUpdate.model_validate({field: None})
    assert "값을 비울 수 없습니다" in str(exc.value)


def test_update_null_assignee_and_due_allowed() -> None:
    data = TaskUpdate.model_validate(
        {"assignee_id": None, "due_date": None, "description": None}
    )
    assert data.model_fields_set == {"assignee_id", "due_date", "description"}
    assert data.assignee_id is None and data.due_date is None


def test_update_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({"created_by": 1})


def test_task_out_shape(db: Session) -> None:
    owner = make_user(db, name="지수")
    project = make_project(db, owner)
    task = make_task(db, project, owner, due_date=date(2026, 11, 14))

    body = TaskOut.model_validate(task).model_dump(mode="json")

    assert set(body) == {
        "id",
        "project_id",
        "title",
        "description",
        "status",
        "priority",
        "assignee",
        "due_date",
        "created_by",
        "completed_at",
        "created_at",
        "updated_at",
    }
    assert body["created_by"] == {
        "id": owner.id,
        "login_id": owner.login_id,
        "name": "지수",
    }
    assert body["assignee"] is None
    assert body["status"] == "TODO" and body["priority"] == "MEDIUM"
    assert body["due_date"] == "2026-11-14"
    assert body["completed_at"] is None
    assert body["created_at"].endswith("Z")


def test_task_out_with_assignee(db: Session) -> None:
    owner = make_user(db)
    member = make_user(db, name="민호")
    project = make_project(db, owner)
    task = make_task(db, project, owner, assignee_id=member.id)

    body = TaskOut.model_validate(task).model_dump(mode="json")

    assert body["assignee"] == {
        "id": member.id,
        "login_id": member.login_id,
        "name": "민호",
    }
