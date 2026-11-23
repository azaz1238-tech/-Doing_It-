"""댓글 요청·응답 스키마 (API-SPEC §6 "댓글", CMT-01·02).

- 내용: 앞뒤 공백 제거 후 1~300자. 빈 댓글·초과는 422.
- Comment: user는 TaskComment.author 관계에서 읽는다.
  화면은 updated_at이 created_at과 다르면 "수정됨"을 표시한다(초 단위).
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import UtcDatetime
from app.schemas.task import UserBrief

CommentContent = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: CommentContent


class CommentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: CommentContent


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    user: UserBrief = Field(validation_alias="author")
    content: str
    created_at: UtcDatetime
    updated_at: UtcDatetime
