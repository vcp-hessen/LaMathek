"""loan line status_before_end for terminal corrections

Revision ID: 20261018_0032
Revises: 20261018_0031
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261018_0032"
down_revision = "20261018_0031"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _column_exists("loan_lines", "status_before_end"):
        op.add_column(
            "loan_lines",
            sa.Column("status_before_end", sa.String(length=24), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("loan_lines", "status_before_end"):
        op.drop_column("loan_lines", "status_before_end")
