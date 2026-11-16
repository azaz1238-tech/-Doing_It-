"""p0_initial — P0 테이블 5개 (DB 스키마 스크립트)

근거: DATABASE-DESIGN v1.1 §2·§4·§5·§8.1.
users, projects, project_members, tasks, task_activities.
CHECK 12개와 login_id 콜레이션(utf8mb4_bin)은 리뷰 때 DATABASE-DESIGN §4와 대조한다.

Revision ID: 0001
Revises:
Create Date: 2026-11-16 14:12:53.204092

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """P0 테이블 5개를 FK 순서대로 만든다 (users → projects → members → tasks → activities)."""
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "login_id", sa.String(length=20, collation="utf8mb4_bin"), nullable=False
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column(
            "system_role", sa.String(length=10), server_default="USER", nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False
        ),
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
            "login_id REGEXP '^[a-z0-9]{4,20}$'", name=op.f("ck_users_login_id_format")
        ),
        sa.CheckConstraint(
            "system_role IN ('ADMIN','USER')", name=op.f("ck_users_system_role")
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(TRIM(name)) > 0", name=op.f("ck_users_name_not_blank")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("login_id", name=op.f("uq_users_login_id")),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
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
            "CHAR_LENGTH(TRIM(name)) > 0", name=op.f("ck_projects_name_not_blank")
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_projects_period"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_projects_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_table(
        "project_members",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('OWNER','MEMBER')", name=op.f("ck_project_members_role")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_members_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_project_members_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_members")),
        sa.UniqueConstraint(
            "project_id", "user_id", name="uq_project_members_project_user"
        ),
    )
    op.create_index(
        "ix_project_members_user_id", "project_members", ["user_id"], unique=False
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="TODO", nullable=False
        ),
        sa.Column(
            "priority", sa.String(length=10), server_default="MEDIUM", nullable=False
        ),
        sa.Column("assignee_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
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
            "(status = 'DONE') = (completed_at IS NOT NULL)",
            name=op.f("ck_tasks_completed_at"),
        ),
        sa.CheckConstraint(
            "priority IN ('LOW','MEDIUM','HIGH','URGENT')",
            name=op.f("ck_tasks_priority"),
        ),
        sa.CheckConstraint(
            "status IN ('TODO','IN_PROGRESS','DONE')", name=op.f("ck_tasks_status")
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(TRIM(title)) > 0", name=op.f("ck_tasks_title_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_tasks_assignee_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_tasks_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_tasks_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index(
        "ix_tasks_assignee_status", "tasks", ["assignee_id", "status"], unique=False
    )
    op.create_index(
        "ix_tasks_project_status", "tasks", ["project_id", "status"], unique=False
    )
    op.create_table(
        "task_activities",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("field", sa.String(length=20), nullable=True),
        sa.Column("old_value", sa.String(length=255), nullable=True),
        sa.Column("new_value", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(action = 'UPDATED' AND field IS NOT NULL AND field IN ('status','assignee_id','due_date','priority')) OR (action IN ('CREATED','DELETED') AND field IS NULL)",
            name=op.f("ck_task_activities_field"),
        ),
        sa.CheckConstraint(
            "action IN ('CREATED','UPDATED','DELETED')",
            name=op.f("ck_task_activities_action"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_task_activities_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_task_activities_task_id_tasks"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_task_activities_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_activities")),
    )
    op.create_index(
        "ix_task_activities_project",
        "task_activities",
        ["project_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_task_activities_task",
        "task_activities",
        ["task_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """만든 순서의 반대로 테이블을 지운다.

    drop_index를 따로 하지 않는다: 인덱스가 FK에 쓰이고 있어 MariaDB가 먼저 지우는 것을 막는다.
    테이블을 지우면 인덱스도 함께 지워진다.
    """
    op.drop_table("task_activities")
    op.drop_table("tasks")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")
