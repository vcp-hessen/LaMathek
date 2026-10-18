"""calendar feed tokens

Revision ID: 20261018_0038
Revises: 20261018_0037
"""

from alembic import op
import sqlalchemy as sa

revision = "20261018_0038"
down_revision = "20261018_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendar_feeds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.UniqueConstraint("user_id", "scope", "inventory_id", name="uq_calendar_feed_scope"),
    )


def downgrade() -> None:
    op.drop_table("calendar_feeds")
