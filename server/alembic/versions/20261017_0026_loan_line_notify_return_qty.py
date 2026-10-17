"""loan line request_notified and returned_quantity

Revision ID: 20261017_0026
Revises: 20261016_0025
Create Date: 2026-10-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20261017_0026"
down_revision = "20261016_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.add_column(
            sa.Column(
                "request_notified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("returned_quantity", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.drop_column("returned_quantity")
        batch_op.drop_column("request_notified")
