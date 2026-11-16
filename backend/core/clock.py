"""오늘 날짜 = 한국 날짜 (API-SPEC §1.6, ARCHITECTURE §4.6).

- 한국은 서머타임이 없어 UTC+9 고정으로 계산한다 (zoneinfo·tzdata를 쓰지 않는다).
- DB의 CURRENT_DATE는 쓰지 않는다 (DB 세션은 UTC).
- 라우터에서 Depends(get_today)로 받고, 테스트는 app.dependency_overrides로 날짜를 고정한다.
"""

from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def get_today() -> date:
    return datetime.now(KST).date()
