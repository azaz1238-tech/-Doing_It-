"""댓글 서비스 (T-F4-03, CMT-01·02, API-SPEC §6 "댓글").

- 작성·조회: 업무가 속한 프로젝트의 멤버 누구나. 업무 없음 404 → 비멤버 403(task_service.get_task).
- 수정·삭제: 댓글 없음 404 COMMENT_NOT_FOUND → 비멤버 403 NOT_PROJECT_MEMBER →
  작성자가 아니면 403 FORBIDDEN. OWNER도 남의 댓글은 고칠 수 없다(SPEC CMT-02).
  작성자 여부는 역할이 아니라 "누가 썼나"라서 permissions.py가 아니라 여기서 본다.
- 댓글은 변경 이력 대상이 아니다(LOG-01 범위).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Task, TaskComment, User
from app.schemas.comment import CommentCreate, CommentUpdate
from app.services import task_service
from app.services.permissions import ANY_MEMBER, require_project_role
from core.exceptions import Forbidden, NotFound
from core.pagination import PageParams


def list_comments(
    db: Session, user: User, task_id: int, params: PageParams
) -> tuple[list[TaskComment], int]:
    """업무 댓글 목록, 오래된 순(created_at, id) (CMT-01)."""
    task_service.get_task(db, user, task_id)
    condition = TaskComment.task_id == task_id
    total = db.scalar(select(func.count()).select_from(TaskComment).where(condition))
    items = db.scalars(
        select(TaskComment)
        .where(condition)
        .order_by(TaskComment.created_at, TaskComment.id)
        .offset(params.offset)
        .limit(params.size)
        # 응답의 user를 댓글마다 따로 조회하지 않게 한 번에 읽는다(N+1 방지)
        .options(selectinload(TaskComment.author))
    ).all()
    return list(items), total or 0


def create_comment(
    db: Session, user: User, task_id: int, data: CommentCreate
) -> TaskComment:
    """댓글 작성 (CMT-01). 멤버 누구나."""
    task: Task = task_service.get_task(db, user, task_id)
    comment = TaskComment(task_id=task.id, user_id=user.id, content=data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)  # created_at·updated_at(DB 기본값)을 읽는다
    return comment


def update_comment(
    db: Session, user: User, comment_id: int, data: CommentUpdate
) -> TaskComment:
    """본인 댓글 수정 (CMT-02). 내용이 바뀌면 updated_at이 바뀐다."""
    comment = _own_comment(db, user, comment_id)
    comment.content = data.content
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, user: User, comment_id: int) -> None:
    """본인 댓글 삭제 (CMT-02)."""
    comment = _own_comment(db, user, comment_id)
    db.delete(comment)
    db.commit()


def _own_comment(db: Session, user: User, comment_id: int) -> TaskComment:
    """댓글 404 → 비멤버 403 → 작성자가 아니면 403 FORBIDDEN (§1.5)."""
    comment = db.get(TaskComment, comment_id)
    if comment is None:
        raise NotFound("COMMENT_NOT_FOUND", "댓글을 찾을 수 없습니다")
    task = db.get(Task, comment.task_id)
    require_project_role(db, task.project_id, user, ANY_MEMBER)
    if comment.user_id != user.id:
        raise Forbidden("FORBIDDEN", "권한이 없습니다")
    return comment
