"""remove general (loan-role) photos on loans

Revision ID: 20261018_0033
Revises: 20261018_0032
"""

from alembic import op

revision = "20261018_0033"
down_revision = "20261018_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM photos WHERE loan_id IS NOT NULL "
        "AND (loan_photo_role IS NULL OR loan_photo_role = 'loan')"
    )


def downgrade() -> None:
    pass
