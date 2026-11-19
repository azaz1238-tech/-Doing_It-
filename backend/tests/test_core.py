"""core/ 스타터킷 테스트 (T-F0-08) — DB 없이 동작한다.

완료 기준: 잘못된 토큰 401, 422 공통 형식.
app/ 대신 테스트 전용 작은 앱으로 core/만 검사한다(스타터킷 분리 확인).
"""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field

from core.auth import get_token_user_id
from core.clock import get_today
from core.config import get_settings
from core.exceptions import (
    BusinessRuleError,
    Conflict,
    Forbidden,
    NotFound,
    register_exception_handlers,
)
from core.pagination import Page, PageParams
from core.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class ItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=30)


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/me")
    def me(user_id: Annotated[int, Depends(get_token_user_id)]) -> dict:
        return {"user_id": user_id}

    @app.post("/items")
    def create_item(
        body: ItemIn, user_id: Annotated[int, Depends(get_token_user_id)]
    ) -> dict:
        return {"title": body.title}

    @app.get("/items", response_model=Page[int])
    def list_items(params: Annotated[PageParams, Depends()]) -> dict:
        data = list(range(1, 46))
        page = data[params.offset : params.offset + params.size]
        return {
            "items": page,
            "total": len(data),
            "page": params.page,
            "size": params.size,
        }

    @app.get("/today")
    def today(today: Annotated[date, Depends(get_today)]) -> dict:
        return {"today": today.isoformat()}

    @app.get("/errors/{kind}")
    def errors(kind: str) -> None:
        raise {
            "400": BusinessRuleError(
                "ASSIGNEE_NOT_MEMBER", "담당자는 프로젝트 멤버여야 합니다"
            ),
            "403": Forbidden("NOT_PROJECT_MEMBER", "프로젝트 멤버가 아닙니다"),
            "404": NotFound("TASK_NOT_FOUND", "업무를 찾을 수 없습니다"),
            "409": Conflict("LOGIN_ID_ALREADY_EXISTS", "이미 사용 중인 아이디입니다"),
            "500": RuntimeError("비밀 정보가 담긴 내부 오류"),
        }[kind]

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_make_app(), raise_server_exceptions=False)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 인증: 잘못된 토큰 401 ──


def test_valid_token_returns_user_id(client):
    res = client.get("/me", headers=_auth(create_access_token(7)))
    assert res.status_code == 200
    assert res.json() == {"user_id": 7}


@pytest.mark.parametrize(
    "headers",
    [
        {},  # 헤더 없음
        {"Authorization": "Bearer"},  # 토큰 없음
        {"Authorization": "Basic abc"},  # Bearer 아님
        {"Authorization": "Bearer not-a-jwt"},  # 형식 오류
    ],
)
def test_missing_or_malformed_token_401(client, headers):
    res = client.get("/me", headers=headers)
    assert res.status_code == 401
    assert res.json() == {"code": "UNAUTHORIZED", "message": "로그인이 필요합니다"}
    assert res.headers["www-authenticate"] == "Bearer"


def test_wrong_signature_401(client):
    token = jwt.encode(
        {"sub": "7", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "x" * 40,  # 다른 키
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/me", headers=_auth(token)).status_code == 401


def test_expired_token_401(client):
    token = jwt.encode(
        {"sub": "7", "exp": datetime.now(UTC) - timedelta(seconds=1)},
        get_settings().jwt_secret_key,
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/me", headers=_auth(token)).status_code == 401


def test_token_without_exp_or_sub_401(client):
    key = get_settings().jwt_secret_key
    no_exp = jwt.encode({"sub": "7"}, key, algorithm=JWT_ALGORITHM)
    no_sub = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(hours=1)}, key, algorithm=JWT_ALGORITHM
    )
    assert client.get("/me", headers=_auth(no_exp)).status_code == 401
    assert client.get("/me", headers=_auth(no_sub)).status_code == 401


def test_none_algorithm_token_rejected():
    token = jwt.encode({"sub": "7", "exp": 9999999999}, None, algorithm="none")
    assert decode_access_token(token) is None


def test_token_payload_has_only_sub_and_exp():
    token = create_access_token(3)
    payload = jwt.decode(
        token, get_settings().jwt_secret_key, algorithms=[JWT_ALGORITHM]
    )
    assert set(payload) == {"sub", "exp"}
    assert payload["sub"] == "3"
    # 만료 2시간 (ACCESS_TOKEN_EXPIRE_MINUTES=120)
    remaining = payload["exp"] - datetime.now(UTC).timestamp()
    assert 0 < remaining <= get_settings().access_token_expire_minutes * 60


def test_auth_checked_before_validation(client):
    # 검사 순서 401 → 422 (API-SPEC §1.5): 토큰 없이 잘못된 본문을 보내도 401
    res = client.post("/items", json={"title": ""})
    assert res.status_code == 401


# ── 422 공통 형식 ──


def test_validation_error_format(client):
    token = create_access_token(1)
    res = client.post(
        "/items", json={"title": "", "project_id": 9}, headers=_auth(token)
    )
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "입력값을 확인해 주세요"
    assert "detail" not in body
    fields = {e["field"]: e["message"] for e in body["errors"]}
    assert fields["title"] == "1자 이상 입력해 주세요"
    assert fields["project_id"] == "정의되지 않은 필드입니다"


def test_validation_missing_field(client):
    res = client.post("/items", json={}, headers=_auth(create_access_token(1)))
    assert res.status_code == 422
    assert res.json()["errors"] == [{"field": "title", "message": "필수 항목입니다"}]


# ── 그 외 오류 형식 ──


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("400", 400, "ASSIGNEE_NOT_MEMBER"),
        ("403", 403, "NOT_PROJECT_MEMBER"),
        ("404", 404, "TASK_NOT_FOUND"),
        ("409", 409, "LOGIN_ID_ALREADY_EXISTS"),
    ],
)
def test_app_error_format(client, kind, status, code):
    res = client.get(f"/errors/{kind}")
    assert res.status_code == status
    assert set(res.json()) == {"code", "message"}
    assert res.json()["code"] == code


def test_unknown_path_404(client):
    res = client.get("/no-such-path")
    assert res.status_code == 404
    assert res.json() == {"code": "NOT_FOUND", "message": "요청한 경로가 없습니다"}


def test_wrong_method_405(client):
    # /items는 GET·POST만 있다 (API-SPEC §2, SPEC-CHANGELOG #19)
    res = client.delete("/items")
    assert res.status_code == 405
    assert res.json() == {
        "code": "METHOD_NOT_ALLOWED",
        "message": "허용되지 않는 요청 방식입니다",
    }
    # Allow 헤더가 유지된다 (Starlette는 처음 맞은 경로의 메서드만 적는다)
    assert res.headers["allow"]


def test_unhandled_error_500_hides_detail(client):
    res = client.get("/errors/500")
    assert res.status_code == 500
    assert res.json() == {
        "code": "INTERNAL_ERROR",
        "message": "서버 오류가 발생했습니다",
    }
    assert "비밀" not in res.text


# ── 페이지네이션 ──


def test_pagination_default_and_offset(client):
    assert client.get("/items").json() == {
        "items": list(range(1, 21)),
        "total": 45,
        "page": 1,
        "size": 20,
    }
    assert client.get("/items?page=3&size=20").json()["items"] == list(range(41, 46))


@pytest.mark.parametrize(
    ("query", "field", "message"),
    [
        ("page=0", "page", "1 이상이어야 합니다"),
        ("size=0", "size", "1 이상이어야 합니다"),
        ("size=101", "size", "100 이하여야 합니다"),
        ("size=abc", "size", "정수를 입력해 주세요"),
    ],
)
def test_pagination_out_of_range_422(client, query, field, message):
    res = client.get(f"/items?{query}")
    assert res.status_code == 422
    assert res.json()["errors"] == [{"field": field, "message": message}]


def test_pagination_max_size_100_ok(client):
    assert client.get("/items?size=100").json()["size"] == 100


# ── 비밀번호 ──


def test_password_hash_and_verify():
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert verify_password("password123", hashed)
    assert not verify_password("password124", hashed)


def test_verify_password_over_72_bytes_returns_false():
    hashed = hash_password("password123")
    assert verify_password("가" * 25, hashed) is False  # 75바이트 → 예외 대신 False


# ── 오늘 (한국 날짜) ──


def test_today_is_kst_and_overridable():
    app = _make_app()
    app.dependency_overrides[get_today] = lambda: date(2026, 11, 20)
    assert TestClient(app).get("/today").json() == {"today": "2026-11-20"}


def test_get_today_uses_utc_plus_9():
    kst_today = (datetime.now(UTC) + timedelta(hours=9)).date()
    assert get_today() == kst_today
