"""공통 예외와 예외 처리기 (ARCHITECTURE §4.5, API-SPEC §1.4).

- 서비스는 HTTPException 대신 AppError 계열을 던진다.
- 모든 오류 응답은 { code, message } 형식이고, 422만 errors 목록을 더한다.
- 스타터킷 파일이므로 app/를 import하지 않는다.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """업무 오류의 기본 클래스. status_code·code·message로 응답을 만든다."""

    status_code = 500
    code = "INTERNAL_ERROR"
    message = "서버 오류가 발생했습니다."

    def __init__(
        self,
        code: str | None = None,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code or self.code
        self.message = message or self.message
        self.headers = headers
        super().__init__(self.message)


class BusinessRuleError(AppError):
    status_code = 400
    code = "BAD_REQUEST"
    message = "요청을 처리할 수 없습니다."


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "로그인이 필요합니다."

    def __init__(self, code: str | None = None, message: str | None = None) -> None:
        # OAuth2 Bearer 규격(RFC 6750): 401에는 WWW-Authenticate 헤더를 붙인다
        super().__init__(code, message, headers={"WWW-Authenticate": "Bearer"})


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "권한이 없습니다."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "요청한 대상을 찾을 수 없습니다."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "이미 존재합니다."


# pydantic 오류 종류 → 한국어 메시지. 필드별 문구가 필요하면 스키마 검증 함수에서 ValueError로 직접 쓴다.
_VALIDATION_MESSAGES = {
    "missing": "필수 항목입니다.",
    "extra_forbidden": "정의되지 않은 필드입니다.",
    "string_too_short": "{min_length}자 이상 입력해 주세요.",
    "string_too_long": "{max_length}자 이하로 입력해 주세요.",
    "string_pattern_mismatch": "형식이 올바르지 않습니다.",
    "string_type": "문자열을 입력해 주세요.",
    "int_type": "정수를 입력해 주세요.",
    "int_parsing": "정수를 입력해 주세요.",
    "bool_type": "true 또는 false를 입력해 주세요.",
    "bool_parsing": "true 또는 false를 입력해 주세요.",
    "greater_than": "{gt}보다 커야 합니다.",
    "greater_than_equal": "{ge} 이상이어야 합니다.",
    "less_than": "{lt}보다 작아야 합니다.",
    "less_than_equal": "{le} 이하여야 합니다.",
    "date_type": "날짜 형식(YYYY-MM-DD)으로 입력해 주세요.",
    "date_parsing": "날짜 형식(YYYY-MM-DD)으로 입력해 주세요.",
    "date_from_datetime_parsing": "날짜 형식(YYYY-MM-DD)으로 입력해 주세요.",
    "enum": "허용된 값 중 하나를 입력해 주세요.",
    "literal_error": "허용된 값 중 하나를 입력해 주세요.",
    "json_invalid": "JSON 형식이 올바르지 않습니다.",
    "model_attributes_type": "객체 형식이어야 합니다.",
    "dict_type": "객체 형식이어야 합니다.",
    "list_type": "목록 형식이어야 합니다.",
}
_DEFAULT_VALIDATION_MESSAGE = "입력값이 올바르지 않습니다."


def _validation_message(error: dict) -> str:
    error_type = error.get("type", "")
    if error_type == "value_error":
        # 스키마 검증 함수에서 raise ValueError("한국어 문구") 한 경우 그 문구를 그대로 쓴다
        message = str(error.get("msg", ""))
        return message.removeprefix("Value error, ") or _DEFAULT_VALIDATION_MESSAGE
    template = _VALIDATION_MESSAGES.get(error_type)
    if template is None:
        return _DEFAULT_VALIDATION_MESSAGE
    try:
        return template.format(**(error.get("ctx") or {}))
    except (KeyError, IndexError):
        return _DEFAULT_VALIDATION_MESSAGE


def _error_body(code: str, message: str) -> dict:
    return {"code": code, "message": message}


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message),
        headers=exc.headers,
    )


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        loc = error.get("loc") or ()
        # field = 오류 위치의 마지막 이름 (본문 필드명 또는 쿼리 이름)
        field = str(loc[-1]) if loc else ""
        errors.append({"field": field, "message": _validation_message(error)})
    body = _error_body("VALIDATION_ERROR", "입력값을 확인해 주세요.")
    body["errors"] = errors
    return JSONResponse(status_code=422, content=body)


async def _http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404, content=_error_body("NOT_FOUND", "요청한 경로가 없습니다.")
        )
    # 404 외(405 등)는 명세에 코드가 없어 FastAPI 기본 처리를 따른다
    return await http_exception_handler(request, exc)


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # 상세 내용은 서버 로그에만 남긴다. 쿼리 문자열·헤더·본문(토큰·비밀번호)은 남기지 않는다
    logger.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", "서버 오류가 발생했습니다."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
