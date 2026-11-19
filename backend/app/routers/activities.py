"""변경 이력 조회 API (API-SPEC §6 "변경 이력", T-F4-05, LOG-03). 인증 필요.

라우터는 요청 검증·인증·서비스 호출·응답 모양만 맡는다. 조회(404)·권한(403)은
activity_service가 한다(ARCHITECTURE §4.2).
response_model_exclude_unset: old_assignee·new_assignee는 담당자 이력에만 키가 있게 한다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.activity import ActivityOut
from app.services import activity_service
from app.services.auth_service import get_current_user
from core.db import get_db
from core.pagination import Page, PageParams

router = APIRouter(tags=["activities"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
Paging = Annotated[PageParams, Depends()]


@router.get(
    "/tasks/{task_id}/activities",
    response_model=Page[ActivityOut],
    response_model_exclude_unset=True,
)
def list_task_activities(
    task_id: int, user: CurrentUser, db: DbSession, params: Paging
) -> Page[ActivityOut]:
    """업무 상세의 이력 탭 (LOG-03-a). 최신순."""
    items, total = activity_service.list_task_activities(db, user, task_id, params)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.get(
    "/projects/{project_id}/activities",
    response_model=Page[ActivityOut],
    response_model_exclude_unset=True,
)
def list_project_activities(
    project_id: int, user: CurrentUser, db: DbSession, params: Paging
) -> Page[ActivityOut]:
    """프로젝트 최근 활동 (LOG-03-b, 화면은 size=20). 삭제된 업무 이력 포함."""
    items, total = activity_service.list_project_activities(
        db, user, project_id, params
    )
    return Page(items=items, total=total, page=params.page, size=params.size)
