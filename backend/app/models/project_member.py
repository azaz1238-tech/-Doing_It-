"""project_members 테이블 (P0) — 사용자와 프로젝트를 잇고 역할을 저장한다.

근거: DATABASE-DESIGN §4.3·§5·§8.1, REQUIREMENTS PRJ-04·05.
"OWNER 최소 1명"은 여러 행에 걸친 규칙이라 DB가 아니라 서비스 계층에서 검사한다(400 LAST_OWNER).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        # 같은 사람을 두 번 추가하면 409 ALREADY_MEMBER. 멤버십 확인 조회에도 이 인덱스를 쓴다.
        UniqueConstraint(
            "project_id", "user_id", name="uq_project_members_project_user"
        ),
        CheckConstraint("role IN ('OWNER','MEMBER')", name="role"),
        # 내 프로젝트 목록 (PRJ-02)
        Index("ix_project_members_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 프로젝트가 삭제되면 멤버십도 함께 삭제
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    # ProjectRole 값. 역할 비교는 services/permissions.py에서만 한다.
    role: Mapped[str] = mapped_column(String(10))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
