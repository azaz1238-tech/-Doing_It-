"""인증 도메인 서비스 (ARCHITECTURE §4.1·§4.4).

- signup: 회원가입 (T-F1-01)
- get_current_user: T-F1-03에서 이 파일에 추가한다
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import SignupRequest
from core.exceptions import Conflict
from core.security import hash_password

# MariaDB 오류 번호: UNIQUE 위반
_ER_DUP_ENTRY = 1062


def signup(db: Session, data: SignupRequest) -> User:
    user = User(
        login_id=data.login_id,
        password_hash=hash_password(data.password),
        name=data.name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # 미리 SELECT로 확인하지 않고 UNIQUE에 맡긴다 → 동시에 가입해도 한 명만 성공
        if exc.orig.args[0] == _ER_DUP_ENTRY:
            raise Conflict(
                "LOGIN_ID_ALREADY_EXISTS", "이미 사용 중인 아이디입니다"
            ) from exc
        raise
    return user
