"""업무 API (API-SPEC §5.4, T-F2-07~09). 모든 엔드포인트에 인증이 필요하다.

라우터는 요청 검증·인증·서비스 호출·응답 모양만 맡는다. 조회(404)·권한(403)·이력·커밋은
task_service가 한다(ARCHITECTURE §4.2).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import TaskStatus
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import task_service
from app.services.auth_service import get_current_user
from core.db import get_db
from core.pagination import Page, PageParams

router = APIRouter(tags=["tasks"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/projects/{project_id}/tasks", response_model=Page[TaskOut])
def list_tasks(
    project_id: int,
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
) -> Page[TaskOut]:
    """업무 목록·칸반 (TASK-05). 칸반은 상태(컬럼)마다 1번씩 호출한다."""
    tasks, total = task_service.list_tasks(db, user, project_id, task_status, params)
    return Page(
        items=[TaskOut.model_validate(task) for task in tasks],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    project_id: int, body: TaskCreate, user: CurrentUser, db: DbSession
) -> TaskOut:
    """업무 등록 (TASK-01·03·04). 상태는 항상 TODO, CREATED 이력을 함께 남긴다."""
    task = task_service.create_task(db, user, project_id, body)
    return TaskOut.model_validate(task)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: CurrentUser, db: DbSession) -> TaskOut:
    """업무 상세 (TASK-06). 업무가 속한 프로젝트의 멤버만."""
    return TaskOut.model_validate(task_service.get_task(db, user, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, body: TaskUpdate, user: CurrentUser, db: DbSession
) -> TaskOut:
    """업무 수정·상태 변경 (TASK-02·03·06, LOG-01·02). 보낸 필드만 바꾼다."""
    return TaskOut.model_validate(task_service.update_task(db, user, task_id, body))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: CurrentUser, db: DbSession) -> Response:
    """업무 삭제 (TASK-06). OWNER·작성자만. 이력은 task_id NULL로 남는다."""
    task_service.delete_task(db, user, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
