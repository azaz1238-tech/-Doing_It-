"""pytest 공통 픽스처 — 테스트 DB 준비와 테스트마다 비우기.

근거: ARCHITECTURE §7, DATABASE-DESIGN §9.
- 테스트 DB는 .env의 TEST_DATABASE_URL(doing_it_test). 개발 DB는 건드리지 않는다.
- 세션 시작 시 alembic upgrade head로 테이블을 만든다(마이그레이션 자체도 매번 검증됨).
- 테스트 함수마다 모든 테이블을 TRUNCATE한다. 트랜잭션 롤백 방식은 쓰지 않는다:
  동시성 테스트(OWNER 동시 제거)가 실제로 커밋해야 하기 때문이다.
- API 테스트용 client(TestClient) 픽스처는 app/main.py(T-F0-04)가 생긴 뒤 여기에 추가한다.
  ⚠ 그때 반드시 app.dependency_overrides[get_db]로 테스트 DB 세션을 넣는다.
  빠뜨리면 API가 core.db.engine(= 개발 DB, DATABASE_URL)에 쓰고, 위 _test 안전장치도 우회된다.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from core.db import create_db_engine  # import하면 load_dotenv()가 실행된다

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """테스트 DB engine. 처음 한 번 마이그레이션을 최신으로 올린다."""
    test_engine = create_db_engine(TEST_DATABASE_URL)
    # 안전장치: 실수로 개발 DB 주소가 들어오면 TRUNCATE 전에 멈춘다.
    db_name = test_engine.url.database or ""
    if not db_name.endswith("_test"):
        pytest.exit(
            f"TEST_DATABASE_URL이 테스트 DB가 아닙니다: {db_name}", returncode=1
        )

    @event.listens_for(test_engine, "connect")
    def _short_lock_wait(dbapi_connection, _connection_record):
        # 앞 테스트가 세션·스레드를 안 닫고 끝나면 TRUNCATE가 잠금을 기다린다.
        # MariaDB 기본값(86400초 = 하루) 대신 10초 뒤 오류로 끝나게 한다.
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET SESSION lock_wait_timeout = 10")

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["sqlalchemy.url"] = TEST_DATABASE_URL  # alembic/env.py가 읽는다
    config.attributes["configure_logger"] = False  # 테스트 로그 설정을 건드리지 않게
    command.upgrade(config, "head")

    yield test_engine
    test_engine.dispose()


@pytest.fixture(autouse=True)
def _truncate_tables(engine: Engine) -> None:
    """모든 테스트 시작 전에 테이블을 비운다(앞 테스트가 중간에 죽어도 깨끗하게 시작)."""
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        try:
            for table in Base.metadata.sorted_tables:
                conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        finally:
            # 중간에 실패해도 반드시 켠다. 꺼진 채 연결 풀로 돌아가면
            # 다음 테스트에서 FK 위반이 조용히 통과한다.
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """테스트 DB 세션. 데이터를 남기려면 테스트에서 직접 commit()한다."""
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
