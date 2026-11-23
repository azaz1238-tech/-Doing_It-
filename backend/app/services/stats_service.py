"""프로젝트 통계·내 대시보드 (P1: DASH-03·04, 이후 DASH-02도 여기). 읽기만 하고 커밋하지 않는다.

검사 순서는 API-SPEC §1.5: 프로젝트 없음 404 → 비멤버 403 (require_project_role).
"""

from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Project, ProjectMember, Task, User
from app.models.enums import TaskStatus
from app.services.permissions import ANY_MEMBER, require_project_role
from core.pagination import PageParams

# 마감 임박 = 오늘 ~ 오늘 + 3일 (REQUIREMENTS DASH-03, SPEC Q1). DASH-03·04가 같이 쓴다.
DUE_SOON_DAYS = 3


def alert_of(due_date: date | None, today: date) -> str | None:
    """지연·임박 판정 (DASH-03·04 같은 기준). 마감일이 오늘이면 임박."""
    if due_date is None:
        return None
    if due_date < today:
        return "OVERDUE"
    if due_date <= today + timedelta(days=DUE_SOON_DAYS):
        return "DUE_SOON"
    return None


def list_deadlines(
    db: Session, user: User, project_id: int, today: date
) -> tuple[list[Task], list[Task]]:
    """(지연, 임박) 업무 목록. 미완료이고 마감일이 있는 업무만. 마감일 순 → id 순.

    today는 라우터가 get_today()(한국 날짜)로 넘긴다. DB의 CURRENT_DATE는 쓰지 않는다(§1.6).
    """
    require_project_role(db, project_id, user, ANY_MEMBER)

    tasks = db.scalars(
        select(Task)
        .where(
            Task.project_id == project_id,
            Task.status != TaskStatus.DONE,
            Task.due_date.is_not(None),
            Task.due_date <= today + timedelta(days=DUE_SOON_DAYS),
        )
        .order_by(Task.due_date, Task.id)
        # 응답의 assignee·created_by를 업무마다 따로 조회하지 않게 한 번에 읽는다(N+1 방지)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
    ).all()

    # 쿼리 한 번으로 읽고 나눈다(DATABASE-DESIGN DASH-03 쿼리와 같은 조건). 정렬은 그대로 유지된다.
    overdue = [t for t in tasks if t.due_date < today]
    due_soon = [t for t in tasks if t.due_date >= today]
    return overdue, due_soon


def list_my_tasks(
    db: Session, user: User, today: date, params: PageParams
) -> tuple[list[tuple[Task, int, str]], int]:
    """나에게 할당된 미완료 업무, 모든 프로젝트 (DASH-04). (업무, 프로젝트 id, 이름) 목록과 전체 수.

    정렬: 지연 → 임박 → 나머지, 그룹 안에서 마감일 빠른 순(없음은 뒤) → id (DATABASE-DESIGN §7).
    """
    due_soon_until = today + timedelta(days=DUE_SOON_DAYS)
    group = case(
        (Task.due_date < today, 0),
        (Task.due_date <= due_soon_until, 1),
        else_=2,  # 마감일 없음(NULL 비교는 거짓)도 여기
    )
    # 멤버가 아닌 프로젝트의 업무는 보이지 않게 멤버 행과 묶는다.
    # (멤버를 제거하면 담당이 해제되므로 원래 생기지 않지만, 하위 리소스 접근은 항상 멤버 확인 — CLAUDE.md §5)
    base = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .join(
            ProjectMember,
            (ProjectMember.project_id == Task.project_id)
            & (ProjectMember.user_id == user.id),
        )
        .where(Task.assignee_id == user.id, Task.status != TaskStatus.DONE)
    )

    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.execute(
        base.add_columns(Project.id, Project.name)
        .order_by(group, Task.due_date.is_(None), Task.due_date, Task.id)
        .offset(params.offset)
        .limit(params.size)
        # 응답의 assignee·created_by를 업무마다 따로 조회하지 않게 한 번에 읽는다(N+1 방지)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
    ).all()
    return [(task, pid, pname) for task, pid, pname in rows], total or 0
