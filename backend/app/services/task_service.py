"""업무 도메인 서비스 (T-F2-07~09, ARCHITECTURE §4.3·§4.4).

- 함수는 라우터가 require_project_role()로 얻은 ProjectMember를 받는다
  (멤버 확인은 라우터에서 이미 끝난 상태).
- 서비스 함수 하나 = 트랜잭션 하나. 업무 변경과 이력 기록(activity_service)을 함께
  add한 뒤 마지막에 한 번 커밋한다. 중간에 실패하면 get_db가 롤백한다.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ProjectMember, Task
from app.models.enums import ActivityAction, TaskStatus, priority_order
from app.schemas.task import TaskCreate
from app.services import activity_service
from core.exceptions import NotFound
from core.pagination import PageParams


def create_task(db: Session, member: ProjectMember, data: TaskCreate) -> Task:
    """업무 등록 + CREATED 이력 (TASK-01, LOG-01). 상태는 항상 TODO."""
    # TODO(T-F3-04): data.assignee_id가 이 프로젝트 멤버가 아니면 400 ASSIGNEE_NOT_MEMBER
    task = Task(
        project_id=member.project_id,
        created_by=member.user_id,
        status=TaskStatus.TODO,
        **data.model_dump(),
    )
    db.add(task)
    db.flush()  # task.id를 얻어 이력에 넣는다
    activity_service.record(db, task, member.user_id, ActivityAction.CREATED)
    db.commit()
    return task


def list_tasks(
    db: Session, project_id: int, status: TaskStatus | None, params: PageParams
) -> tuple[list[Task], int]:
    """칸반 목록 (TASK-05). (이번 페이지 업무, 전체 개수)를 돌려준다.

    정렬: 우선순위 높은 순 → 마감일 빠른 순(없음은 뒤) → id (DATABASE-DESIGN §7).
    """
    conditions = [Task.project_id == project_id]
    if status is not None:
        conditions.append(Task.status == status)

    total = db.scalar(select(func.count()).select_from(Task).where(*conditions))
    items = db.scalars(
        select(Task)
        .where(*conditions)
        .order_by(
            priority_order(Task.priority),
            Task.due_date.is_(None),
            Task.due_date,
            Task.id,
        )
        .offset(params.offset)
        .limit(params.size)
        # 응답의 assignee·created_by를 업무마다 따로 조회하지 않게 한 번에 읽는다(N+1 방지)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
    ).all()
    return list(items), total or 0


def get_task_or_404(db: Session, task_id: int) -> Task:
    """업무 조회. 없으면 404 TASK_NOT_FOUND (멤버 확인보다 먼저, API-SPEC §1.5)."""
    task = db.get(Task, task_id)
    if task is None:
        raise NotFound("TASK_NOT_FOUND", "업무를 찾을 수 없습니다")
    return task
