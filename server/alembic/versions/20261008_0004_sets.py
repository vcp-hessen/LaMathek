"""sets, piece membership, set stock lines

Revision ID: 20261008_0004
Revises: 20261008_0003
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_0004"
down_revision: Union[str, None] = "20261008_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_id"], ["inventories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inventory_id", "name", name="uq_set_per_inventory"),
    )
    with op.batch_alter_table("pieces") as batch_op:
        batch_op.add_column(sa.Column("set_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("set_role", sa.String(length=16), nullable=True))
        batch_op.create_foreign_key(
            "fk_pieces_set_id",
            "sets",
            ["set_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_table(
        "set_stock_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=False),
        sa.Column("material_type_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_set_stock_line_quantity_positive"),
        sa.ForeignKeyConstraint(["set_id"], ["sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "set_id", "material_type_id", "role", name="uq_set_stock_line"
        ),
    )


def downgrade() -> None:
    op.drop_table("set_stock_lines")
    with op.batch_alter_table("pieces") as batch_op:
        batch_op.drop_constraint("fk_pieces_set_id", type_="foreignkey")
        batch_op.drop_column("set_role")
        batch_op.drop_column("set_id")
    op.drop_table("sets")
