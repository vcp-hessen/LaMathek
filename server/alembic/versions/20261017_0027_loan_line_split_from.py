"""loan line split_from_line_id

Revision ID: 20261017_0027
Revises: 20261017_0026
"""

from alembic import op
import sqlalchemy as sa

revision = "20261017_0027"
down_revision = "20261017_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.add_column(
            sa.Column("split_from_line_id", sa.Integer(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_loan_lines_split_from_line_id",
            "loan_lines",
            ["split_from_line_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.drop_constraint(
            "fk_loan_lines_split_from_line_id",
            type_="foreignkey",
        )
        batch_op.drop_column("split_from_line_id")
