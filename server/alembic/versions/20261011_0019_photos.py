"""photos table for file-backed images

Revision ID: 20261011_0019
Revises: 20261011_0018
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0019"
down_revision: Union[str, None] = "20261011_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("piece_id", sa.Integer(), nullable=True),
        sa.Column("stock_lot_id", sa.Integer(), nullable=True),
        sa.Column("set_id", sa.Integer(), nullable=True),
        sa.Column("material_type_id", sa.Integer(), nullable=True),
        sa.Column("damage_id", sa.Integer(), nullable=True),
        sa.Column("inventory_id", sa.Integer(), nullable=True),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(CASE WHEN piece_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN stock_lot_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN set_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN material_type_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN damage_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN inventory_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN loan_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_photo_single_owner",
        ),
        sa.ForeignKeyConstraint(["damage_id"], ["damages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_type_id"], ["material_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["piece_id"], ["pieces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_id"], ["sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_lot_id"], ["stock_lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("photos")
