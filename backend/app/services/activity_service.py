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

from sqlalchemy.orm import Session

from app.models import Task, TaskActivity
from app.models.enums import ActivityAction, ActivityField

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
