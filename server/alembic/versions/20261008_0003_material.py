"""material types, pieces, stocks

Revision ID: 20261008_0003
Revises: 20261008_0002
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_0003"
down_revision: Union[str, None] = "20261008_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tracking", sa.String(length=16), nullable=False),
        sa.Column("variant_label", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["inventory_id"], ["inventories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "inventory_id", "name", name="uq_material_type_per_inventory"
        ),
    )
    op.create_table(
        "material_type_variant_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_type_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_type_id",
            "value",
            name="uq_material_type_variant_value",
        ),
    )
    op.create_table(
        "pieces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("variant", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_type_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material_type_id", name="uq_stock_per_material_type"),
    )


def downgrade() -> None:
    op.drop_table("stocks")
    op.drop_table("pieces")
    op.drop_table("material_type_variant_values")
    op.drop_table("material_types")
