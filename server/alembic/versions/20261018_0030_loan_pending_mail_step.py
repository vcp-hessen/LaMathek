"""loan pending_mail_step

Revision ID: 20261018_0030
Revises: 20261018_0029
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_0030"
down_revision = "20261018_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("loans", sa.Column("pending_mail_step", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("loans", "pending_mail_step")
