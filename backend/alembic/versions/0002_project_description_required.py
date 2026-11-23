"""project_description_required — 프로젝트 설명 필수

근거: 11/22 팀장 결정 (명세 반영 예정: DATABASE-DESIGN projects.description, SPEC-CHANGELOG).
projects.description을 NOT NULL로 바꾸고, 공백만 있는 값을 막는 CHECK를 더한다.
이미 설명이 없거나 공백뿐인 프로젝트는 '설명 없음'으로 채운 뒤 제약을 건다
(팀원 로컬 DB에 테스트용 프로젝트가 남아 있어도 마이그레이션이 실패하지 않게).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLACEHOLDER = "설명 없음"


def upgrade() -> None:
    """빈 설명을 채우고 NOT NULL + 공백 금지 CHECK를 건다."""
    op.execute(
        sa.text(
            "UPDATE projects SET description = :placeholder "
            "WHERE description IS NULL OR CHAR_LENGTH(TRIM(description)) = 0"
        ).bindparams(placeholder=PLACEHOLDER)
    )
    op.alter_column("projects", "description", existing_type=sa.Text(), nullable=False)
    op.create_check_constraint(
        op.f("ck_projects_description_not_blank"),
        "projects",
        "CHAR_LENGTH(TRIM(description)) > 0",
    )


def downgrade() -> None:
    """제약만 되돌린다. 채워 넣은 '설명 없음'은 그대로 둔다."""
    op.drop_constraint(
        op.f("ck_projects_description_not_blank"), "projects", type_="check"
    )
    op.alter_column("projects", "description", existing_type=sa.Text(), nullable=True)
