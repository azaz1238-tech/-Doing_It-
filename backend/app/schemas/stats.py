"""프로젝트 통계·내 대시보드 응답 스키마 (API-SPEC §6, DASH-03·04)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.task import TaskOut

Alert = Literal["OVERDUE", "DUE_SOON"]


class DeadlinesOut(BaseModel):
    """마감 임박·지연 (DASH-03). 집계 결과라 페이지네이션하지 않는다 (API-SPEC §1.3)."""

    overdue: list[TaskOut]  # 마감일 < 오늘
    due_soon: list[TaskOut]  # 오늘 <= 마감일 <= 오늘 + 3일 (오늘이면 임박)


class ProjectBrief(BaseModel):
    id: int
    name: str


class MyTaskOut(TaskOut):
    """내 업무 대시보드 항목 (DASH-04, API-SPEC §6). Task + 프로젝트 요약 + 경고."""

    # TaskOut 값을 그대로 넘겨 만들 수 있게 created_by 이름으로도 받는다
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    project: ProjectBrief
    alert: Alert | None  # 지연 OVERDUE · 임박 DUE_SOON · 나머지 null
