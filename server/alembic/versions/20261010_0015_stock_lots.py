"""stock lots replace a single quantity per material type

Revision ID: 20261010_0015
Revises: 20261009_0014
Create Date: 2026-10-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_0015"
down_revision: Union[str, None] = "20261009_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_lots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_type_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("variant", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_stock_lot_quantity_non_negative"),
        sa.ForeignKeyConstraint(
            ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO stock_lots (material_type_id, label, variant, quantity) "
            "SELECT material_type_id, NULL, NULL, quantity FROM stocks"
        )
    )
    op.drop_table("stocks")


def downgrade() -> None:
    raise NotImplementedError
