"""initial schema

Revision ID: 20261008_0001
Revises:
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oidc_sub", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_superuser", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("oidc_sub"),
    )
    op.create_index("ix_users_oidc_sub", "users", ["oidc_sub"], unique=False)

    op.create_table(
        "installation_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=512), nullable=False),
        sa.CheckConstraint("id = 1", name="installation_settings_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO installation_settings (id, title, subtitle) "
            "VALUES (1, 'VCP Hessen', 'Landesmaterial')"
        )
    )


def downgrade() -> None:
    op.drop_table("installation_settings")
    op.drop_index("ix_users_oidc_sub", table_name="users")
    op.drop_table("users")
