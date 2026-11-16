"""DB 연결: engine, 세션, get_db() 의존성.

근거: ARCHITECTURE §4.1·§4.3, DATABASE-DESIGN §10.
"""

import os
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# TODO(T-F0-04): core/config.py(설정 객체)가 생기면 거기서 DATABASE_URL을 읽도록 바꾼다.
# load_dotenv()는 이 파일 위치에서 위쪽 폴더로 올라가며 .env를 찾는다(저장소 루트의 .env).
load_dotenv()


def create_db_engine(url: str) -> Engine:
    """연결마다 세션 시간대를 UTC로 맞춘 engine을 만든다.

    개발 DB와 테스트 DB(TEST_DATABASE_URL)가 같은 설정을 쓰도록 함수로 둔다.
    """
    # pool_pre_ping: 오래 쉬어 끊긴 연결을 쓰기 전에 확인한다.
    engine = create_engine(url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _set_utc(dbapi_connection, _connection_record):
        # DATETIME은 시간대를 저장하지 않으므로 세션을 UTC로 고정한다.
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET time_zone = '+00:00'")

    return engine


engine = create_db_engine(os.environ["DATABASE_URL"])
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """요청마다 세션 1개를 열고, 예외가 나면 롤백, 끝나면 닫는다.

    커밋하지 않는다. 쓰기 서비스 함수가 마지막에 한 번 커밋한다(ARCHITECTURE §4.3).
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
