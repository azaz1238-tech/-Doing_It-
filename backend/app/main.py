"""FastAPI 앱 진입점 (ARCHITECTURE §4.1).

실행: backend 폴더에서 `uvicorn app.main:app --reload`
"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, users
from core.config import get_settings
from core.exceptions import register_exception_handlers

# 모든 API 경로 앞에 붙는 접두어 (API-SPEC §1.1)
API_PREFIX = "/api"

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict[str, str]:
    """서버 동작 확인용. 인증 없음, DB 조회·사용자 데이터 없음 (API-SPEC §1.2, CONSTITUTION 6-1 예외)."""
    return {"status": "ok"}


def create_app() -> FastAPI:
    # 설정이 잘못되면 여기서 ConfigError로 시작을 멈춘다 (JWT_SECRET_KEY 32자 미만 등)
    settings = get_settings()

    app = FastAPI(title="동잇(Doing_It) API")

    # CORS는 .env의 FRONTEND_ORIGIN 하나만 허용한다. 토큰은 헤더로 보내므로 쿠키 자격 증명은 쓰지 않는다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # 오류 응답을 { code, message } 공통 형식으로 (422는 errors 추가)
    register_exception_handlers(app)

    # 기능 라우터는 여기에 prefix=API_PREFIX로 추가한다 (auth·users·projects·members·tasks)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)

    return app


app = create_app()
