"""inventory visibility (internal, active, archived)

Revision ID: 20261012_0022
Revises: 20261012_0021
Create Date: 2026-10-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0022"
down_revision: Union[str, None] = "20261012_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("inventories", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "visibility",
                sa.String(length=16),
                nullable=False,
                server_default="internal",
            )
        )
        batch_op.create_check_constraint(
            "ck_inventory_visibility",
            "visibility IN ('internal', 'active', 'archived')",
        )


def downgrade() -> None:
    raise NotImplementedError
