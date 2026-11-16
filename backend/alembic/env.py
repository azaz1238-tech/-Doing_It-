"""Alembic 실행 설정.

근거: DATABASE-DESIGN §1-1·§2·§10, ARCHITECTURE §7.
- DB 주소는 alembic.ini가 아니라 .env의 DATABASE_URL에서 읽는다(비밀번호를 Git에 올리지 않음).
- pytest는 config.attributes["sqlalchemy.url"]에 TEST_DATABASE_URL을 넣어 테스트 DB에 적용한다.
- 연결은 core.db.create_db_engine()으로 만든다 → 앱과 똑같이 세션 시간대가 UTC.
- alembic.ini에는 한글을 쓰지 않는다. 한국어 Windows가 .ini를 cp949로 읽어 UTF-8 한글이 깨진다.
"""

import os
from logging.config import fileConfig

from alembic import context

from app.models import Base
from core.db import create_db_engine  # import하면 load_dotenv()가 실행된다

config = context.config

# pytest는 configure_logger=False를 넘긴다 → 테스트의 로그 설정(caplog 등)을 바꾸지 않는다.
if config.config_file_name is not None and config.attributes.get(
    "configure_logger", True
):
    # disable_existing_loggers=False: 이미 만들어진 앱 로거를 끄지 않는다.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# autogenerate가 비교할 대상: app/models/__init__.py에 등록된 테이블 5개
target_metadata = Base.metadata


def get_url() -> str:
    return config.attributes.get("sqlalchemy.url") or os.environ["DATABASE_URL"]


def run_migrations_offline() -> None:
    """DB에 접속하지 않고 SQL만 출력한다 (alembic upgrade head --sql)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """DB에 접속해 마이그레이션을 실행한다."""
    engine = create_db_engine(get_url())
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
