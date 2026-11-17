"""인증 API (API-SPEC §5.1). 인증 없이 부를 수 있는 API는 회원가입·로그인뿐이다."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenOut, UserOut
from app.services import auth_service
from core.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Annotated[Session, Depends(get_db)]) -> User:
    return auth_service.signup(db, body)


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenOut:
    return auth_service.login(db, body)
