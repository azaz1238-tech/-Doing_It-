"""p1_comments — 업무 댓글 테이블 + P1 마감 인덱스

근거: DATABASE-DESIGN v1.4 §2·§4.6·§8.1, SPEC-CHANGELOG #25.
- task_comments (CMT-01·02): 내용 VARCHAR(300) + 공백만 있는 값 금지 CHECK,
  업무 삭제 시 CASCADE, 작성자는 RESTRICT(사용자 행은 지우지 않음).
- ix_tasks_project_due (DASH-03 마감 임박·지연): §8.1에 있었지만 어느 리비전에도 없던 인덱스.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_comments",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(TRIM(content)) > 0",
            name=op.f("ck_task_comments_content_not_blank"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_task_comments_task_id_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_task_comments_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_comments")),
    )
    op.create_index("ix_task_comments_task", "task_comments", ["task_id", "created_at"])
    op.create_index("ix_tasks_project_due", "tasks", ["project_id", "due_date"])


def downgrade() -> None:
    op.drop_index("ix_tasks_project_due", table_name="tasks")
    op.drop_table("task_comments")  # 테이블과 함께 ix_task_comments_task도 지워진다
