"""stock loss entries for loan restore

Revision ID: 20261018_0035
Revises: 20261018_0034
"""

from alembic import op
import sqlalchemy as sa

revision = "20261018_0035"
down_revision = "20261018_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_loss_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_line_id", sa.Integer(), nullable=True),
        sa.Column("material_type_id", sa.Integer(), nullable=False),
        sa.Column("stock_lot_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("variant_signature", sa.Text(), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["loan_line_id"], ["loan_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["stock_lot_id"], ["stock_lots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("stock_loss_entries")
