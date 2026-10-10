"""loan kind short or permanent

Revision ID: 20261009_0008
Revises: 20261009_0007
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0008"
down_revision: Union[str, None] = "20261009_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("loans") as batch_op:
        batch_op.add_column(
            sa.Column(
                "kind",
                sa.String(length=16),
                nullable=False,
                server_default="short",
            )
        )
        batch_op.create_check_constraint(
            "ck_loan_kind",
            "kind IN ('short', 'permanent')",
        )


def downgrade() -> None:
    with op.batch_alter_table("loans") as batch_op:
        batch_op.drop_constraint("ck_loan_kind", type_="check")
        batch_op.drop_column("kind")
