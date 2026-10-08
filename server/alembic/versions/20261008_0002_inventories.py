"""inventories and permissions

Revision ID: 20261008_0002
Revises: 20261008_0001
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_0002"
down_revision: Union[str, None] = "20261008_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_ROLES = ("materialwart", "verantwortliche")


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=32),
                nullable=False,
                server_default="materialwart",
            )
        )

    op.create_table(
        "inventories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "inventory_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "inventory_id", name="uq_inventory_permission"),
    )


def downgrade() -> None:
    op.drop_table("inventory_permissions")
    op.drop_table("inventories")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
