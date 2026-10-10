"""set short_name

Revision ID: 20261009_0014
Revises: 20261009_0013
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0014"
down_revision: Union[str, None] = "20261009_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("short_name", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint(
            "uq_set_short_name_per_inventory",
            ["inventory_id", "short_name"],
        )


def downgrade() -> None:
    with op.batch_alter_table("sets", schema=None) as batch_op:
        batch_op.drop_constraint("uq_set_short_name_per_inventory", type_="unique")
        batch_op.drop_column("short_name")
