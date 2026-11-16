"""tasks 테이블 (P0).

근거: DATABASE-DESIGN §4.4·§5·§8.1, REQUIREMENTS TASK-01~06.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CASE_SENSITIVE, Base, TimestampMixin
from app.models.enums import TaskPriority, TaskStatus


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("CHAR_LENGTH(TRIM(title)) > 0", name="title_not_blank"),
        CheckConstraint("status IN ('TODO','IN_PROGRESS','DONE')", name="status"),
        CheckConstraint(
            "priority IN ('LOW','MEDIUM','HIGH','URGENT')", name="priority"
        ),
        # DONE이면 completed_at이 반드시 있고, DONE이 아니면 반드시 NULL.
        CheckConstraint(
            "(status = 'DONE') = (completed_at IS NOT NULL)", name="completed_at"
        ),
        # 칸반 컬럼 조회 (TASK-05)
        Index("ix_tasks_project_status", "project_id", "status"),
        # 멤버 제거 시 담당 업무 찾기, P1 내 업무·담당자별 현황
        Index("ix_tasks_assignee_status", "assignee_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 프로젝트가 삭제되면 업무도 함께 삭제 (PRJ-03)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE")
    )
    # 앞뒤 공백 제거 후 1~30자 (TASK-01)
    title: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    # 생성은 항상 TODO (API는 status를 받지 않는다)
    status: Mapped[str] = mapped_column(
        String(20, collation=CASE_SENSITIVE),
        default=TaskStatus.TODO,
        server_default=TaskStatus.TODO.value,
    )
    priority: Mapped[str] = mapped_column(
        String(10, collation=CASE_SENSITIVE),
        default=TaskPriority.MEDIUM,
        server_default=TaskPriority.MEDIUM.value,
    )
    # 담당자는 없을 수 있다. 프로젝트 멤버인지는 서비스 계층에서 검사(TASK-03).
    # SET NULL은 안전장치이고, 실제 담당 해제는 서비스가 이력과 함께 처리한다.
    assignee_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    # 수정·삭제 권한 판단에 쓴다 (TASK-06)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    # 과거 날짜·프로젝트 기간 밖 날짜도 허용
    due_date: Mapped[date | None] = mapped_column(Date)
    # DONE이 될 때 기록, 다른 상태로 바뀌면 NULL (서비스가 처리, CHECK가 보장)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
