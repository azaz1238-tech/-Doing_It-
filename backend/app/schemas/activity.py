"""변경 이력 응답 스키마 (API-SPEC §6 "변경 이력" Activity, LOG-03).

- task_title: 업무가 있으면 tasks.title. 삭제된 업무(task_id null)는 DELETED 행만
  자기 old_value(삭제 전 제목), 같은 업무의 다른 행은 None (SPEC-CHANGELOG #20).
- old_assignee·new_assignee: field가 assignee_id인 행에서만 값을 넣는다(None 포함).
  다른 행은 넣지 않아 라우터의 response_model_exclude_unset으로 키가 빠진다.
"""

from pydantic import BaseModel

from app.models.enums import ActivityAction, ActivityField
from app.schemas.common import UtcDatetime
from app.schemas.task import UserBrief


class ActivityOut(BaseModel):
    id: int
    task_id: int | None
    task_title: str | None
    user: UserBrief
    action: ActivityAction
    field: ActivityField | None
    old_value: str | None
    new_value: str | None
    old_assignee: UserBrief | None = None
    new_assignee: UserBrief | None = None
    created_at: UtcDatetime
