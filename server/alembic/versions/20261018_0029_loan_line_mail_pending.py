"""loan line mail_pending

Revision ID: 20261018_0029
Revises: 20261017_0028
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_0029"
down_revision = "20261017_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "loan_lines",
        sa.Column(
            "mail_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("loan_lines", "mail_pending")
