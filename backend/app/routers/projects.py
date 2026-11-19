"""프로젝트 API (API-SPEC §5.2). 모든 엔드포인트에 인증이 필요하다."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import ProjectRole
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import project_service
from app.services.auth_service import get_current_user
from core.db import get_db
from core.pagination import Page, PageParams

router = APIRouter(prefix="/projects", tags=["projects"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, user: CurrentUser, db: DbSession) -> ProjectOut:
    """프로젝트 생성 (PRJ-01). 만든 사람이 OWNER가 된다."""
    project = project_service.create_project(db, user, body)
    return ProjectOut.of(project, ProjectRole.OWNER)


@router.get("", response_model=Page[ProjectOut])
def list_projects(
    user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()]
) -> Page[ProjectOut]:
    """내 프로젝트 목록 (PRJ-02). 내가 멤버인 것만, 최근 생성순. 진행률 포함 (DASH-01)."""
    rows, total = project_service.list_my_projects(db, user, params.offset, params.size)
    progress = project_service.get_progress(db, [project.id for project, _ in rows])
    return Page(
        items=[
            ProjectOut.of(project, role, progress[project.id]) for project, role in rows
        ],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, user: CurrentUser, db: DbSession) -> ProjectOut:
    """프로젝트 상세 (PRJ-07). 멤버만 볼 수 있다."""
    project, role = project_service.get_project(db, user, project_id)
    progress = project_service.get_one_progress(db, project.id)
    return ProjectOut.of(project, role, progress)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, body: ProjectUpdate, user: CurrentUser, db: DbSession
) -> ProjectOut:
    """프로젝트 수정 (PRJ-03). OWNER만. 보낸 필드만 바꾼다."""
    project, role = project_service.update_project(db, user, project_id, body)
    progress = project_service.get_one_progress(db, project.id)
    return ProjectOut.of(project, role, progress)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, user: CurrentUser, db: DbSession) -> Response:
    """프로젝트 삭제 (PRJ-03). OWNER만. 이름 확인 절차는 화면에서만 한다."""
    project_service.delete_project(db, user, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
