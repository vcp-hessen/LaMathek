"""installation settings calendar bundesland

Revision ID: 20261018_0039
Revises: 20261018_0038
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_0039"
down_revision = "20261018_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "calendar_bundesland",
                sa.String(length=2),
                nullable=False,
                server_default="HE",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.drop_column("calendar_bundesland")
