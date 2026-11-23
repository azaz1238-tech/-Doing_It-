"""프로젝트 통계 (P1: DASH-03, 이후 DASH-02도 여기). 읽기만 하고 커밋하지 않는다.

검사 순서는 API-SPEC §1.5: 프로젝트 없음 404 → 비멤버 403 (require_project_role).
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Task, User
from app.models.enums import TaskStatus
from app.services.permissions import ANY_MEMBER, require_project_role

# 마감 임박 = 오늘 ~ 오늘 + 3일 (REQUIREMENTS DASH-03, SPEC Q1). DASH-04도 이 값을 쓴다.
DUE_SOON_DAYS = 3


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
