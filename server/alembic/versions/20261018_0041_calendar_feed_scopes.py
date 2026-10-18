"""calendar feed scope borrower vs legacy user

Revision ID: 20261018_0041
Revises: 20261018_0040
"""

from alembic import op

revision = "20261018_0041"
down_revision = "20261018_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE calendar_feeds SET scope = 'borrower' WHERE scope = 'user'")


def downgrade() -> None:
    op.execute(
        "UPDATE calendar_feeds SET scope = 'user' WHERE scope = 'borrower' AND inventory_id IS NULL"
    )
