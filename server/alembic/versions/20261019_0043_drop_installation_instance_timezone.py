"""drop installation_settings.instance_timezone (use LAMATHEK_INSTANCE_TIMEZONE)

Revision ID: 20261019_0043
Revises: 20261019_0042
"""

import sqlalchemy as sa
from alembic import op

revision = "20261019_0043"
down_revision = "20261019_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("installation_settings")}
    if "instance_timezone" not in columns:
        return
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.drop_column("instance_timezone")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("installation_settings")}
    if "instance_timezone" in columns:
        return
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "instance_timezone",
                sa.String(length=64),
                nullable=False,
                server_default="Europe/Berlin",
            )
        )
