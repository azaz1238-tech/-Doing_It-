"""프로젝트 통계 응답 스키마 (API-SPEC §6 "통계", DASH-03)."""

from pydantic import BaseModel

from app.schemas.task import TaskOut


class DeadlinesOut(BaseModel):
    """마감 임박·지연 (DASH-03). 집계 결과라 페이지네이션하지 않는다 (API-SPEC §1.3)."""

    overdue: list[TaskOut]  # 마감일 < 오늘
    due_soon: list[TaskOut]  # 오늘 <= 마감일 <= 오늘 + 3일 (오늘이면 임박)
