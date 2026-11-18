"""멤버 API (API-SPEC §5.3). 모든 엔드포인트에 인증이 필요하다."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.member import MemberAdd, MemberOut
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


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int, body: MemberAdd, user: CurrentUser, db: DbSession
) -> MemberOut:
    """멤버 추가 (PRJ-04). OWNER만. 알림·수락 절차 없이 바로 멤버가 된다."""
    return member_service.add_member(db, user, project_id, body)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int, user_id: int, user: CurrentUser, db: DbSession
) -> Response:
    """멤버 제거 (PRJ-05). OWNER만. 담당하던 업무는 "담당자 없음"이 되고 이력이 남는다."""
    member_service.remove_member(db, user, project_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
