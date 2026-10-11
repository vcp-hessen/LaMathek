"""installation settings privacy disclosure fields

Revision ID: 20261011_0018
Revises: 20261011_0017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0018"
down_revision: Union[str, None] = "20261011_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("host_name", sa.String(length=512), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("host_address", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column(
                "host_privacy_url", sa.String(length=512), nullable=False, server_default=""
            )
        )
        batch_op.add_column(
            sa.Column(
                "auth_provider_name", sa.String(length=512), nullable=False, server_default=""
            )
        )
        batch_op.add_column(
            sa.Column(
                "auth_provider_same_host",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "authority_name", sa.String(length=512), nullable=False, server_default=""
            )
        )
        batch_op.add_column(
            sa.Column(
                "authority_url", sa.String(length=512), nullable=False, server_default=""
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("installation_settings", schema=None) as batch_op:
        batch_op.drop_column("authority_url")
        batch_op.drop_column("authority_name")
        batch_op.drop_column("auth_provider_same_host")
        batch_op.drop_column("auth_provider_name")
        batch_op.drop_column("host_privacy_url")
        batch_op.drop_column("host_address")
        batch_op.drop_column("host_name")
