"""사용자 API (API-SPEC §5.1 GET /users/me, §6 GET /users/me/tasks). 모든 엔드포인트에 인증이 필요하다."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import UserOut
from app.schemas.stats import MyTaskOut, ProjectBrief
from app.schemas.task import TaskOut
from app.services import stats_service
from app.services.auth_service import get_current_user
from core.clock import get_today
from core.db import get_db
from core.pagination import Page, PageParams

router = APIRouter(prefix="/users", tags=["users"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> User:
    """내 정보 조회 (AUTH-04). 새로고침 시 로그인 상태 복원에 쓴다."""
    return user


@router.get("/me/tasks", response_model=Page[MyTaskOut])
def list_my_tasks(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    today: Annotated[date, Depends(get_today)],  # 한국 날짜, 테스트에서 교체
    params: Annotated[PageParams, Depends()],
) -> Page[MyTaskOut]:
    """내 업무 대시보드 (DASH-04). 모든 프로젝트에서 나에게 할당된 미완료 업무."""
    rows, total = stats_service.list_my_tasks(db, user, today, params)
    items = [
        MyTaskOut(
            **TaskOut.model_validate(task).model_dump(),
            project=ProjectBrief(id=pid, name=pname),
            alert=stats_service.alert_of(task.due_date, today),
        )
        for task, pid, pname in rows
    ]
    return Page(items=items, total=total, page=params.page, size=params.size)
