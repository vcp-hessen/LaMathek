"""Drop global user role column."""

from alembic import op
import sqlalchemy as sa

revision = "20261011_0017"
down_revision = "20261011_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=32),
                server_default="materialwart",
                nullable=False,
            )
        )
