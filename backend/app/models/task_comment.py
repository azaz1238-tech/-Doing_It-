"""task_comments 테이블 (P1, 리비전 0003) — 업무 댓글.

근거: DATABASE-DESIGN §4.6·§5·§8.1, REQUIREMENTS CMT-01·02.
- 내용은 앞뒤 공백 제거 후 1~300자. 길이·공백은 스키마가 422로 막고, 공백만 있는 값은 CHECK가 한 번 더 막는다.
- 본인만 수정·삭제(CMT-02) — 서비스 계층에서 검사한다. 수정하면 updated_at이 바뀌어 화면이 "수정됨"을 표시한다.
- 업무가 삭제되면 DB CASCADE로 함께 삭제. 작성자(users)는 지우지 않으므로 RESTRICT.
"""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.user import User


class TaskComment(TimestampMixin, Base):
    __tablename__ = "task_comments"
    __table_args__ = (
        CheckConstraint("CHAR_LENGTH(TRIM(content)) > 0", name="content_not_blank"),
        # 댓글 목록 (created_at, id 순). InnoDB 보조 인덱스는 PK(id)를 끝에 품는다.
        Index("ix_task_comments_task", "task_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    content: Mapped[str] = mapped_column(String(300))

    # 응답의 user(UserBrief)를 만들 때 쓴다. 목록은 selectinload로 한 번에 읽는다.
    author: Mapped[User] = relationship()
