"""loan returns and return lines

Revision ID: 20261008_0006
Revises: 20261008_0005
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_0006"
down_revision: Union[str, None] = "20261008_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loan_returns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "loan_return_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_return_id", sa.Integer(), nullable=False),
        sa.Column("loan_line_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('returned', 'loss')",
            name="ck_loan_return_line_outcome",
        ),
        sa.CheckConstraint(
            "(quantity IS NULL) OR (quantity > 0)",
            name="ck_loan_return_line_quantity_positive",
        ),
        sa.ForeignKeyConstraint(["loan_line_id"], ["loan_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loan_return_id"], ["loan_returns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("loan_return_lines")
    op.drop_table("loan_returns")
