"""projects 테이블 (P0).

근거: DATABASE-DESIGN §4.2·§5, REQUIREMENTS PRJ-01.
"""

from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("CHAR_LENGTH(TRIM(name)) > 0", name="name_not_blank"),
        # 둘 중 하나라도 비어 있으면 통과. 둘 다 있으면 종료일 >= 시작일.
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="period",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 앞뒤 공백 제거 후 1~30자 (PRJ-01). 한글도 1자.
    name: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # 사용자 행은 지우지 않는다. 실수로 지우려 하면 오류가 나야 한다 (§5 RESTRICT).
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
