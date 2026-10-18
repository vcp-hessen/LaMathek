"""loan mail receipt send flags

Revision ID: 20261018_0034
Revises: 20261018_0033
"""

from alembic import op
import sqlalchemy as sa

revision = "20261018_0034"
down_revision = "20261018_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "loans",
        sa.Column(
            "mail_sent_borrower",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "loans",
        sa.Column(
            "mail_sent_managers",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("loans", "mail_sent_managers")
    op.drop_column("loans", "mail_sent_borrower")
