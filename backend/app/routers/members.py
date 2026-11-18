"""멤버 API (API-SPEC §5.3). 모든 엔드포인트에 인증이 필요하다."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.member import MemberOut
from app.services import member_service
from app.services.auth_service import get_current_user
from core.db import get_db
from core.pagination import Page, PageParams

router = APIRouter(prefix="/projects/{project_id}/members", tags=["members"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[MemberOut])
def list_members(
    project_id: int,
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
) -> Page[MemberOut]:
    """멤버 목록 (PRJ-07). OWNER 먼저 → 참여순. 담당자 선택지로도 쓴다(화면은 size=100)."""
    items, total = member_service.list_members(
        db, user, project_id, params.offset, params.size
    )
    return Page(items=items, total=total, page=params.page, size=params.size)
