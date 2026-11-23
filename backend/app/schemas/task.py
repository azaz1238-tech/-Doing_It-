"""업무 요청·응답 스키마 (API-SPEC §4·§5.4, REQUIREMENTS TASK-01~06).

- 등록(TaskCreate): status는 받지 않는다(항상 TODO). 정의 안 된 필드는 422.
- 수정(TaskUpdate): 보낸 필드만 바꾼다. 서비스는 model_fields_set으로 "보낸 필드"를 안다.
  title·priority·status는 null 불가(DB에서 NOT NULL), assignee_id·due_date·description은
  null로 해제할 수 있다.
- 담당자가 프로젝트 멤버인지(400 ASSIGNEE_NOT_MEMBER)는 서비스가 검사한다(T-F3-04).
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import Query
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


class TaskFilter:
    """업무 목록 검색·필터 쿼리 (TASK-07, API-SPEC §5.4). 라우터에서 Depends()로 받는다.

    - q: 앞뒤 공백을 지우고, 비면 조건 없음(None).
    - assignee_id: 숫자 또는 "none"(담당자 미지정만). 그 밖의 값은 422.
    - due_from·due_to: 양 끝 포함. 하나라도 있으면 마감일 없는 업무는 빠진다.
    """

    def __init__(
        self,
        q: Annotated[str | None, Query()] = None,
        # int | Literal["none"]로 받으면 422 오류의 field가 union 후보 이름("int")이 되어
        # 패턴으로 검사한 뒤 숫자로 바꾼다. 19자리 제한: BIGINT 범위이고, 아주 긴 숫자가
        # int() 자릿수 한도에 걸려 500이 나는 것을 422로 막는다.
        assignee_id: Annotated[
            str | None, Query(pattern=r"^(none|[0-9]{1,19})$")
        ] = None,
        priority: Annotated[TaskPriority | None, Query()] = None,
        due_from: Annotated[date | None, Query()] = None,
        due_to: Annotated[date | None, Query()] = None,
    ) -> None:
        self.q = (q or "").strip() or None
        self.assignee_id: int | Literal["none"] | None = (
            assignee_id
            if assignee_id is None or assignee_id == "none"
            else int(assignee_id)
        )
        self.priority = priority
        self.due_from = due_from
        self.due_to = due_to


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
