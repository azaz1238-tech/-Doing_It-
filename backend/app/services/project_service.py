"""프로젝트 서비스 (ARCHITECTURE §4.4, API-SPEC §5.2).

my_role은 Project 모델에 없어서 (Project, 역할) 짝으로 돌려주고, 응답 모양은 라우터가 만든다.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, User
from app.models.enums import ProjectRole
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    is_period_valid,
    period_error,
)
from app.services.permissions import ANY_MEMBER, OWNER_ONLY, require_project_role


def create_project(db: Session, user: User, data: ProjectCreate) -> Project:
    """프로젝트 생성 + 만든 사람을 OWNER로 추가. 한 트랜잭션 (PRJ-01)."""
    project = Project(**data.model_dump(), created_by=user.id)
    db.add(project)
    db.flush()  # project.id를 얻는다
    db.add(
        ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER)
    )
    db.commit()
    db.refresh(project)  # DB가 넣은 created_at·updated_at을 읽는다
    return project


def list_my_projects(
    db: Session, user: User, offset: int, limit: int
) -> tuple[list[tuple[Project, str]], int]:
    """내가 멤버인 프로젝트만, 최근 생성순 (PRJ-02, DATABASE-DESIGN §8.2)."""
    total = db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.user_id == user.id)
    )
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        # 같은 초에 만든 프로젝트도 순서가 흔들리지 않게 id로 한 번 더 정렬
        .order_by(Project.created_at.desc(), Project.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [(project, role) for project, role in rows], total


def get_project(db: Session, user: User, project_id: int) -> tuple[Project, str]:
    """프로젝트 상세 (PRJ-07). 없음 404, 비멤버 403 NOT_PROJECT_MEMBER."""
    member = require_project_role(db, project_id, user, ANY_MEMBER)
    return db.get(Project, project_id), member.role


def update_project(
    db: Session, user: User, project_id: int, data: ProjectUpdate
) -> tuple[Project, str]:
    """프로젝트 수정 (PRJ-03). OWNER만. 보낸 필드만 바꾼다."""
    member = require_project_role(db, project_id, user, OWNER_ONLY)
    project = db.get(Project, project_id)

    changes = data.model_dump(exclude_unset=True)
    # 날짜 비교는 저장될 최종 값 기준 (API-SPEC §5.2): end_date만 보내도 기존 start_date와 비교
    start = changes.get("start_date", project.start_date)
    end = changes.get("end_date", project.end_date)
    if not is_period_valid(start, end):
        raise period_error()

    for field, value in changes.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)  # 갱신된 updated_at을 읽는다
    return project, member.role


def delete_project(db: Session, user: User, project_id: int) -> None:
    """프로젝트 삭제 (PRJ-03). OWNER만.

    모델에 ORM 관계가 없어 projects 행만 지운다. 멤버·업무·이력은 DB의 ON DELETE CASCADE로 함께 지워진다.
    """
    require_project_role(db, project_id, user, OWNER_ONLY)
    db.delete(db.get(Project, project_id))
    db.commit()
