"""목록 페이지네이션 (API-SPEC §1.3, NFR-05).

요청: ?page=1&size=20 (page 1~1,000,000, size 1~100, 범위 밖이면 422)
응답: { "items": [...], "total": n, "page": 1, "size": 20 }
집계 API(DASH-02·03, TASK-09)는 페이지네이션하지 않는다.
"""

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
# 상한이 없으면 (page-1)×size가 MariaDB OFFSET 한도를 넘어 SQL 오류(500)가 난다 (#142)
MAX_PAGE = 1_000_000

T = TypeVar("T")


class PageParams:
    """라우터에서 params: Annotated[PageParams, Depends()]로 받는다."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 1,
        size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    ) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
