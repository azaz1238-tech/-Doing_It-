"""상태·역할 같은 값 목록과 우선순위 정렬 식. 이 파일 한곳에만 둔다.

근거: DATABASE-DESIGN §1-2·§7·§10, CONSTITUTION 4-4.
DB에는 MariaDB ENUM 타입이 아니라 VARCHAR + CHECK로 저장한다.
StrEnum이라 TaskStatus.DONE == "DONE"이 참이고, 그대로 문자열로 저장된다.
"""

from enum import StrEnum

from sqlalchemy import case
from sqlalchemy.sql.elements import ColumnElement


class SystemRole(StrEnum):
    """시스템 역할. 가입하면 항상 USER. ADMIN은 P2(ADM-01)."""

    ADMIN = "ADMIN"
    USER = "USER"


class ProjectRole(StrEnum):
    """프로젝트 역할. VIEWER는 만들지 않는다(CONSTITUTION 6-3)."""

    OWNER = "OWNER"
    MEMBER = "MEMBER"


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class TaskPriority(StrEnum):
    """높은 순서대로 적는다. 아래 priority_order()가 이 순서를 쓴다."""

    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActivityAction(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"


class ActivityField(StrEnum):
    """이력을 남기는 항목(LOG-01). 제목·설명 변경은 기록하지 않는다. 값은 컬럼 이름과 같다."""

    STATUS = "status"
    ASSIGNEE_ID = "assignee_id"
    DUE_DATE = "due_date"
    PRIORITY = "priority"


def priority_order(column) -> ColumnElement[int]:
    """우선순위 정렬 식: URGENT=0, HIGH=1, MEDIUM=2, LOW=3.

    priority는 문자열이라 그냥 정렬하면 알파벳순(HIGH→LOW→MEDIUM→URGENT)이 된다.
    칸반 정렬(TASK-05)은 반드시 이 식을 쓴다: .order_by(priority_order(Task.priority), ...)
    """
    return case(
        {p.value: i for i, p in enumerate(TaskPriority)},
        value=column,
    )
