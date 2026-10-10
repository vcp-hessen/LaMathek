"""installation settings website field

Revision ID: 20261009_0012
Revises: 20261009_0011
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0012"
down_revision: Union[str, None] = "20261009_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("website", sa.String(length=512), nullable=False, server_default="")
        )


def downgrade() -> None:
    raise NotImplementedError
