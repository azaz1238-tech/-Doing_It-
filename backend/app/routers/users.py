"""사용자 API (API-SPEC §5.1 GET /users/me). 모든 엔드포인트에 인증이 필요하다."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import User
from app.schemas.auth import UserOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    """내 정보 조회 (AUTH-04). 새로고침 시 로그인 상태 복원에 쓴다."""
    return user
