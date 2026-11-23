"""프로젝트 통계 API (API-SPEC §6, T-F5-05 DASH-03). 인증 필요.

라우터는 요청 검증·인증·서비스 호출·응답 모양만 맡는다. 조회(404)·권한(403)은
stats_service가 한다(ARCHITECTURE §4.2).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.stats import DeadlinesOut
from app.schemas.task import TaskOut
from app.services import stats_service
from app.services.auth_service import get_current_user
from core.clock import get_today
from core.db import get_db

router = APIRouter(tags=["stats"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
Today = Annotated[date, Depends(get_today)]  # 한국 날짜, 테스트에서 교체


@router.get("/projects/{project_id}/stats/deadlines", response_model=DeadlinesOut)
def get_deadlines(
    project_id: int, user: CurrentUser, db: DbSession, today: Today
) -> DeadlinesOut:
    """마감 임박·지연 업무 (DASH-03). 멤버 누구나."""
    overdue, due_soon = stats_service.list_deadlines(db, user, project_id, today)
    return DeadlinesOut(
        overdue=[TaskOut.model_validate(t) for t in overdue],
        due_soon=[TaskOut.model_validate(t) for t in due_soon],
    )
