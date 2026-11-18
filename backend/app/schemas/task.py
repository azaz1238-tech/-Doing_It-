"""업무 요청·응답 스키마 (API-SPEC §4·§5.4, REQUIREMENTS TASK-01~06).

- 등록(TaskCreate): status는 받지 않는다(항상 TODO). 정의 안 된 필드는 422.
- 수정(TaskUpdate): 보낸 필드만 바꾼다. 서비스는 model_fields_set으로 "보낸 필드"를 안다.
  title·priority·status는 null 불가(DB에서 NOT NULL), assignee_id·due_date·description은
  null로 해제할 수 있다.
- 담당자가 프로젝트 멤버인지(400 ASSIGNEE_NOT_MEMBER)는 서비스가 검사한다(T-F3-04).
"""

from datetime import date
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.common import UtcDatetime

# 앞뒤 공백 제거 후 1~30자 (TASK-01)
TaskTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]
# 최대 2000자 (API-SPEC v1.3 §5.4, SPEC-CHANGELOG #15). 없으면 DB TEXT 한도 초과로 500.
# 공백은 지우지 않는다(사용자가 쓴 줄바꿈·들여쓰기 유지).
TaskDescription = Annotated[str, StringConstraints(max_length=2000)]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle
    description: TaskDescription | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdate(BaseModel):
    """바꿀 필드만 보낸다. 기본값 None은 "안 보냄"과 구분하려고 model_fields_set을 쓴다."""

    model_config = ConfigDict(extra="forbid")

    title: TaskTitle | None = None
    description: TaskDescription | None = None
    status: TaskStatus | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    priority: TaskPriority | None = None

    @field_validator("title", "status", "priority", mode="before")
    @classmethod
    def _not_null(cls, value: object) -> object:
        # 기본값(안 보냄)에는 검증이 돌지 않는다 → null을 "보낸" 경우만 막힌다
        if value is None:
            raise ValueError("값을 비울 수 없습니다")
        return value


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login_id: str
    name: str


class TaskOut(BaseModel):
    """Task 객체 (API-SPEC §4). created_by는 Task.creator 관계에서 읽는다."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee: UserBrief | None
    due_date: date | None
    created_by: UserBrief = Field(validation_alias="creator")
    completed_at: UtcDatetime | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
