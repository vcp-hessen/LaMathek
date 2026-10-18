"""calendar feed labels and multiple tokens per scope

Revision ID: 20261018_0040
Revises: 20261018_0039
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_0040"
down_revision = "20261018_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("calendar_feeds", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("label", sa.String(length=255), nullable=False, server_default="")
        )
    op.execute("UPDATE calendar_feeds SET label = 'Kalender' WHERE label = '' OR label IS NULL")
    with op.batch_alter_table("calendar_feeds", schema=None) as batch_op:
        batch_op.drop_constraint("uq_calendar_feed_scope", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("calendar_feeds", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_calendar_feed_scope", ["user_id", "scope", "inventory_id"]
        )
        batch_op.drop_column("label")
