"""인증 의존성 — Authorization: Bearer <token> (API-SPEC §1.2, OAuth2 Bearer 규격).

헤더가 없거나 형식·서명·만료가 틀리면 401 UNAUTHORIZED.
FastAPI 기본값(auto_error=True)은 헤더가 없을 때 403을 내므로 쓰지 않는다.
스타터킷 파일이므로 app/를 import하지 않는다.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.exceptions import Unauthorized
from core.security import decode_access_token

# Swagger(/docs)의 Authorize 버튼도 이 객체로 생긴다
bearer_scheme = HTTPBearer(auto_error=False)


def get_token_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    """토큰을 검증하고 사용자 id를 돌려준다. 사용자 조회·비활성 검사는 get_current_user에서 한다."""
    if credentials is None:
        raise Unauthorized()
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise Unauthorized()
    return user_id
