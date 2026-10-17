"""loan wish pickup/return dates separate from confirmed term dates

Revision ID: 20261016_0024
Revises: 20261012_0023
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261016_0024"
down_revision: Union[str, None] = "20261012_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("loans", sa.Column("wish_pickup_on", sa.Date(), nullable=True))
    op.add_column("loans", sa.Column("wish_return_on", sa.Date(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE loans SET wish_pickup_on = pickup_on, wish_return_on = return_on"
        )
    )


def downgrade() -> None:
    op.drop_column("loans", "wish_return_on")
    op.drop_column("loans", "wish_pickup_on")
