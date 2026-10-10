"""material type fields and categories

Revision ID: 20261009_0010
Revises: 20261009_0009
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0010"
down_revision: Union[str, None] = "20261009_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_category_name"),
    )
    with op.batch_alter_table("material_types", schema=None) as batch_op:
        batch_op.add_column(sa.Column("short_name", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("unit", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("consumable", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_material_types_category_id",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_material_type_short_name_per_inventory",
            ["inventory_id", "short_name"],
        )


def downgrade() -> None:
    raise NotImplementedError
