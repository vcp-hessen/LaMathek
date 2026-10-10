"""damages and repairs

Revision ID: 20261009_0007
Revises: 20261008_0006
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0007"
down_revision: Union[str, None] = "20261008_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "damages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("piece_id", sa.Integer(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("severe", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["piece_id"], ["pieces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "repairs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("damage_id", sa.Integer(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["damage_id"], ["damages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("damage_id", name="uq_repair_per_damage"),
    )


def downgrade() -> None:
    op.drop_table("repairs")
    op.drop_table("damages")
