"""inventory location and installation impressum map center

Revision ID: 20261009_0011
Revises: 20261009_0010
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0011"
down_revision: Union[str, None] = "20261009_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("inventories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))

    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("legal_name", sa.String(length=512), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("legal_address", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("email", sa.String(length=255), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("phone", sa.String(length=64), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("represented_by", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("register", sa.String(length=512), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column(
                "content_responsible", sa.Text(), nullable=False, server_default=""
            )
        )
        batch_op.add_column(
            sa.Column(
                "map_latitude", sa.Float(), nullable=False, server_default="50.65"
            )
        )
        batch_op.add_column(
            sa.Column(
                "map_longitude", sa.Float(), nullable=False, server_default="9.16"
            )
        )


def downgrade() -> None:
    raise NotImplementedError
