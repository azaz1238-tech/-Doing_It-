"""업무 도메인 서비스 (T-F2-07~09, ARCHITECTURE §4.3·§4.4).

- 함수는 라우터가 require_project_role()로 얻은 ProjectMember를 받는다
  (멤버 확인은 라우터에서 이미 끝난 상태).
- 서비스 함수 하나 = 트랜잭션 하나. 업무 변경과 이력 기록(activity_service)을 함께
  add한 뒤 마지막에 한 번 커밋한다. 중간에 실패하면 get_db가 롤백한다.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ProjectMember, Task
from app.models.enums import ActivityAction, TaskStatus, priority_order
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import activity_service
from app.services.permissions import require_task_delete, require_task_edit
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


def update_task(
    db: Session, member: ProjectMember, task: Task, data: TaskUpdate
) -> Task:
    """업무 수정·상태 변경 (TASK-02·06, LOG-01·02). 보낸 필드만 바꾼다.

    한 트랜잭션: 권한 → 값 반영 → completed_at → 바뀐 항목마다 이력 → 커밋 1번.
    """
    fields = data.model_fields_set
    require_task_edit(member, task, fields)  # 403이면 아무것도 바꾸지 않는다
    # TODO(T-F3-04): assignee_id를 보냈고 값이 있으면 멤버인지 검사(400 ASSIGNEE_NOT_MEMBER)

    before = activity_service.snapshot(task)
    for field in fields:
        setattr(task, field, getattr(data, field))

    # DONE이 "되면" 지금, DONE에서 "벗어나면" NULL. DONE→DONE은 그대로 둔다.
    was_done = before["status"] == TaskStatus.DONE
    is_done = task.status == TaskStatus.DONE
    if is_done and not was_done:
        task.completed_at = datetime.now(UTC).replace(tzinfo=None)
    elif was_done and not is_done:
        task.completed_at = None

    activity_service.record_changes(db, task, member.user_id, before)
    db.commit()
    return task


def delete_task(db: Session, member: ProjectMember, task: Task) -> None:
    """업무 삭제 (TASK-06, LOG-01). 실제 삭제하고 이력은 남긴다.

    DELETED 이력(old_value=삭제 전 제목)을 먼저 add한 뒤 삭제한다. 커밋되면 FK
    ON DELETE SET NULL로 이 업무의 이력(CREATED·UPDATED·DELETED) task_id가 모두 NULL이 된다.
    """
    require_task_delete(member, task)
    activity_service.record(
        db, task, member.user_id, ActivityAction.DELETED, old_value=task.title
    )
    db.flush()  # 이력 INSERT를 업무 DELETE보다 먼저 보낸다(FK가 아직 있는 업무를 가리키도록)
    db.delete(task)
    db.commit()
