"""모든 모델이 물려받는 공통 기반.

근거: DATABASE-DESIGN §10 (제약 이름 규칙).
"""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 제약 이름을 규칙대로 자동으로 붙인다. 이름이 있어야 나중에 Alembic이 제약을 지우거나 바꿀 수 있다.
# - CHECK는 모델에서 짧은 이름(예: "login_id_format")만 주면 "ck_users_login_id_format"이 된다.
# - 인덱스·UNIQUE에 이름을 직접 주면(예: "ix_tasks_project_status") 그 이름을 그대로 쓴다.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# 대소문자를 구분하는 콜레이션. 기본 utf8mb4_unicode_ci는 'todo' = 'TODO'로 보아 CHECK를 통과시킨다.
# login_id와 상태·역할 컬럼(enum 값)에 쓴다 (DATABASE-DESIGN §1-7, CONSTITUTION 8-4).
CASE_SENSITIVE = "utf8mb4_bin"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """created_at·updated_at (users·projects·tasks 공통, DATABASE-DESIGN §4 공통 규칙).

    DB 세션이 UTC(core/db.py)라 CURRENT_TIMESTAMP도 UTC 값이 들어간다.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
