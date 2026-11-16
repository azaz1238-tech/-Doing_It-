"""응답 스키마 공통 타입 (ARCHITECTURE §4.6, API-SPEC §1.1).

DB DATETIME은 시간대 없는 UTC 값이다. 응답에서 Z를 붙여 UTC임을 밝힌다.
이 타입을 빼면 화면이 한국 시각으로 착각해 9시간 틀린다.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[
    datetime, PlainSerializer(_to_utc_iso, return_type=str, when_used="json")
]
