"""groups, events, loans, loan lines

Revision ID: 20261008_0005
Revises: 20261008_0004
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_0005"
down_revision: Union[str, None] = "20261008_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_group_name"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_event_name"),
    )
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "loan_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=True),
        sa.Column("piece_id", sa.Integer(), nullable=True),
        sa.Column("material_type_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "("
            "(set_id IS NOT NULL AND piece_id IS NULL AND material_type_id IS NULL AND quantity IS NULL) OR "
            "(set_id IS NULL AND piece_id IS NOT NULL AND material_type_id IS NULL AND quantity IS NULL) OR "
            "(set_id IS NULL AND piece_id IS NULL AND material_type_id IS NOT NULL AND quantity IS NOT NULL AND quantity > 0)"
            ")",
            name="ck_loan_line_kind",
        ),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_type_id"], ["material_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["piece_id"], ["pieces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_id"], ["sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loan_id", "material_type_id", name="uq_loan_line_stock"),
        sa.UniqueConstraint("loan_id", "piece_id", name="uq_loan_line_piece"),
        sa.UniqueConstraint("loan_id", "set_id", name="uq_loan_line_set"),
    )


def downgrade() -> None:
    op.drop_table("loan_lines")
    op.drop_table("loans")
    op.drop_table("events")
    op.drop_table("groups")
