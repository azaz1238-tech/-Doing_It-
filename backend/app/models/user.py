"""users 테이블 (P0).

근거: DATABASE-DESIGN §4.1, REQUIREMENTS AUTH-01.
"""

from sqlalchemy import BigInteger, Boolean, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import SystemRole


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # utf8mb4_bin 콜레이션이라 REGEXP가 대소문자를 구분한다 → 대문자는 DB에서도 막힌다.
        CheckConstraint("login_id REGEXP '^[a-z0-9]{4,20}$'", name="login_id_format"),
        CheckConstraint("system_role IN ('ADMIN','USER')", name="system_role"),
        CheckConstraint("CHAR_LENGTH(TRIM(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 이 컬럼만 _bin. 기본 _ci에서는 REGEXP가 대소문자를 구분하지 않아 'MinHo'도 통과한다.
    login_id: Mapped[str] = mapped_column(
        String(20, collation="utf8mb4_bin"), unique=True
    )
    # bcrypt 해시. 어떤 응답 스키마에도 넣지 않는다.
    password_hash: Mapped[str] = mapped_column(String(255))
    # 앞뒤 공백 제거 후 1~50자 (AUTH-01). 길이 검사는 스키마(Pydantic)가, 공백만은 CHECK도 막는다.
    name: Mapped[str] = mapped_column(String(50))
    system_role: Mapped[str] = mapped_column(
        String(10), default=SystemRole.USER, server_default=SystemRole.USER.value
    )
    # 0이면 403 ACCOUNT_DISABLED
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )
