"""업무 변경 이력 기록 (T-F4-01, LOG-01·02).

근거: DATABASE-DESIGN §4.5, ARCHITECTURE §4.3.
- 이 파일의 함수는 db.add()만 하고 **커밋하지 않는다**. 업무 변경과 같은 트랜잭션에서
  부르고, 부른 서비스 함수가 마지막에 한 번 커밋한다(실패하면 둘 다 취소).
- 이력 대상은 status·assignee_id·due_date·priority 4개. 제목·설명은 기록하지 않는다.
- 값은 문자열로 저장한다: 담당자 "2", 마감일 "2026-11-20", 없음은 NULL.

사용 예 (업무 수정):
    before = snapshot(task)
    ... task 필드 변경 ...
    record_changes(db, task, user_id, before)
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Task, TaskActivity, User
from app.models.enums import ActivityAction, ActivityField
from app.schemas.activity import ActivityOut
from app.schemas.task import UserBrief
from app.services.permissions import ANY_MEMBER, require_project_role
from core.exceptions import NotFound
from core.pagination import PageParams

# 이력을 남기는 필드(ActivityField 값과 같음). 기록 순서도 이 순서다.
TRACKED_FIELDS: tuple[str, ...] = tuple(f.value for f in ActivityField)


def _to_text(value: object) -> str | None:
    """이력 저장용 문자열. None은 그대로 None(NULL)."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)  # StrEnum은 값 그대로("DONE"), int는 "2"


def snapshot(task: Task) -> dict[str, object]:
    """변경 전 값 저장. 이력 대상 4개 필드의 현재 값을 원래 타입 그대로 담는다."""
    return {field: getattr(task, field) for field in TRACKED_FIELDS}


def record(
    db: Session,
    task: Task,
    user_id: int,
    action: ActivityAction,
    field: ActivityField | None = None,
    old_value: object = None,
    new_value: object = None,
) -> TaskActivity:
    """이력 1행 추가(커밋 안 함). 삭제는 old_value에 삭제 전 제목을 넣는다."""
    activity = TaskActivity(
        task_id=task.id,
        project_id=task.project_id,
        user_id=user_id,
        action=action,
        field=field,
        old_value=_to_text(old_value),
        new_value=_to_text(new_value),
    )
    db.add(activity)
    return activity


def record_changes(
    db: Session, task: Task, user_id: int, before: dict[str, object]
) -> int:
    """snapshot() 이후 바뀐 대상 필드마다 UPDATED 1행. 추가한 행 수를 돌려준다.

    문자열로 바꾸기 전 원래 값끼리 비교한다(같은 날짜·같은 값이면 기록 안 함).
    """
    count = 0
    for field in TRACKED_FIELDS:
        old, new = before[field], getattr(task, field)
        if old != new:
            record(
                db,
                task,
                user_id,
                ActivityAction.UPDATED,
                ActivityField(field),
                old,
                new,
            )
            count += 1
    return count


# --- 조회 (T-F4-05, LOG-03) — 읽기만 하고 커밋하지 않는다 ---


def list_task_activities(
    db: Session, user: User, task_id: int, params: PageParams
) -> tuple[list[ActivityOut], int]:
    """업무 하나의 이력, 최신순. 업무 없음 404 → 비멤버 403 (task_service와 같은 순서).

    삭제된 업무는 업무가 없으므로 404다. 그 이력은 프로젝트 최근 이력에서만 보인다.
    """
    # task_service.get_task는 쓰지 않는다(task_service가 이 파일을 import해 순환이 생김)
    task = db.get(Task, task_id)
    if task is None:
        raise NotFound("TASK_NOT_FOUND", "업무를 찾을 수 없습니다")
    require_project_role(db, task.project_id, user, ANY_MEMBER)
    return _page(db, TaskActivity.task_id == task_id, params)


def list_project_activities(
    db: Session, user: User, project_id: int, params: PageParams
) -> tuple[list[ActivityOut], int]:
    """프로젝트 최근 이력, 최신순, 삭제된 업무 이력 포함. 프로젝트 없음 404 → 비멤버 403."""
    require_project_role(db, project_id, user, ANY_MEMBER)
    return _page(db, TaskActivity.project_id == project_id, params)


def _page(db: Session, condition, params: PageParams) -> tuple[list[ActivityOut], int]:
    total = db.scalar(select(func.count()).select_from(TaskActivity).where(condition))
    rows = db.scalars(
        select(TaskActivity)
        .where(condition)
        # 같은 초에 생긴 이력도 순서가 고정되도록 id를 붙인다 (DATABASE-DESIGN §7)
        .order_by(TaskActivity.created_at.desc(), TaskActivity.id.desc())
        .offset(params.offset)
        .limit(params.size)
    ).all()
    return _to_out(db, list(rows)), total or 0


def _to_out(db: Session, rows: list[TaskActivity]) -> list[ActivityOut]:
    """응답 모양으로 바꾼다. 사용자·업무 제목은 행 수와 관계없이 묶음 조회 2번(N+1 방지)."""
    user_ids: set[int] = set()
    for row in rows:
        user_ids.add(row.user_id)
        if row.field == ActivityField.ASSIGNEE_ID:
            user_ids.update(int(v) for v in (row.old_value, row.new_value) if v)
    task_ids = {row.task_id for row in rows if row.task_id is not None}

    users = (
        {
            u.id: UserBrief.model_validate(u)
            for u in db.scalars(select(User).where(User.id.in_(user_ids)))
        }
        if user_ids
        else {}
    )
    titles = (
        # Result는 keys()가 있어 dict()에 그대로 넣으면 매핑으로 오해한다 → 행을 풀어서 담는다
        {
            task_id: title
            for task_id, title in db.execute(
                select(Task.id, Task.title).where(Task.id.in_(task_ids))
            )
        }
        if task_ids
        else {}
    )

    def _assignee(value: str | None) -> UserBrief | None:
        return users[int(value)] if value else None

    result = []
    for row in rows:
        if row.task_id is not None:
            title = titles.get(row.task_id)
        elif row.action == ActivityAction.DELETED:
            title = row.old_value  # 삭제 전 제목
        else:
            title = None  # 같은 업무의 DELETED 행을 찾을 수 없음 (SPEC-CHANGELOG #20)
        data = {
            "id": row.id,
            "task_id": row.task_id,
            "task_title": title,
            "user": users[row.user_id],
            "action": row.action,
            "field": row.field,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "created_at": row.created_at,
        }
        if row.field == ActivityField.ASSIGNEE_ID:
            data["old_assignee"] = _assignee(row.old_value)
            data["new_assignee"] = _assignee(row.new_value)
        result.append(ActivityOut(**data))
    return result
