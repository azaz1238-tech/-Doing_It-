"""task_activities 테이블 (P0) — 업무 변경 이력.

근거: DATABASE-DESIGN §4.5·§5·§8.1, REQUIREMENTS LOG-01·02.
이력 행은 만든 뒤 UPDATE하지 않는다. 그래서 updated_at이 없다.
기록은 업무 변경과 같은 트랜잭션에서 한다(activity_service는 커밋하지 않음).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskActivity(Base):
    __tablename__ = "task_activities"
    __table_args__ = (
        CheckConstraint("action IN ('CREATED','UPDATED','DELETED')", name="action"),
        # 행 모양 강제: UPDATED면 field가 이력 대상 4개 중 하나, CREATED·DELETED면 field는 NULL.
        # field IS NOT NULL이 꼭 필요하다: 없으면 NULL IN (...)이 "알 수 없음"이 되어
        # CHECK를 통과해 버린다(MariaDB CHECK는 거짓일 때만 막음).
        CheckConstraint(
            "(action = 'UPDATED' AND field IS NOT NULL"
            " AND field IN ('status','assignee_id','due_date','priority'))"
            " OR (action IN ('CREATED','DELETED') AND field IS NULL)",
            name="field",
        ),
        # P1 업무 이력 조회 (LOG-03)
        Index("ix_task_activities_task", "task_id", "created_at", "id"),
        # P1 프로젝트 최근 이력 20건
        Index("ix_task_activities_project", "project_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 업무가 삭제돼도 이력은 남는다 → task_id만 NULL이 된다 (CONSTITUTION 8-3)
    task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="SET NULL")
    )
    # 프로젝트가 삭제되면 이력도 함께 삭제
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE")
    )
    # 변경한 사람
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    # ActivityAction 값
    action: Mapped[str] = mapped_column(String(10))
    # ActivityField 값. UPDATED일 때만 있다.
    field: Mapped[str | None] = mapped_column(String(20))
    # 값은 문자열로 저장한다. 담당자는 사용자 id 문자열("3"), 삭제는 old_value에 삭제 전 제목.
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
