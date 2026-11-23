"""댓글 API (API-SPEC §6 "댓글", T-F4-03, CMT-01·02). 인증 필요.

라우터는 요청 검증·인증·서비스 호출·응답 모양만 맡는다. 조회(404)·권한(403)은
comment_service가 한다(ARCHITECTURE §4.2).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.services import comment_service
from app.services.auth_service import get_current_user
from core.db import get_db
from core.pagination import Page, PageParams

router = APIRouter(tags=["comments"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
Paging = Annotated[PageParams, Depends()]


@router.get("/tasks/{task_id}/comments", response_model=Page[CommentOut])
def list_comments(
    task_id: int, user: CurrentUser, db: DbSession, params: Paging
) -> Page[CommentOut]:
    """업무 상세의 댓글 목록 (CMT-01). 오래된 순."""
    items, total = comment_service.list_comments(db, user, task_id, params)
    return Page(
        items=[CommentOut.model_validate(c) for c in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    task_id: int, body: CommentCreate, user: CurrentUser, db: DbSession
) -> CommentOut:
    """댓글 작성 (CMT-01). 멤버 누구나."""
    comment = comment_service.create_comment(db, user, task_id, body)
    return CommentOut.model_validate(comment)


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def update_comment(
    comment_id: int, body: CommentUpdate, user: CurrentUser, db: DbSession
) -> CommentOut:
    """본인 댓글 수정 (CMT-02). OWNER도 남의 댓글은 403."""
    comment = comment_service.update_comment(db, user, comment_id, body)
    return CommentOut.model_validate(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, user: CurrentUser, db: DbSession) -> Response:
    """본인 댓글 삭제 (CMT-02)."""
    comment_service.delete_comment(db, user, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
