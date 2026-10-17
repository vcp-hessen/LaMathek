"""inventory permission role: manage or read

Revision ID: 20261016_0025
Revises: 20261016_0024
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261016_0025"
down_revision: Union[str, None] = "20261016_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "ck_inventory_permission_role"


def _column_exists(table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def _check_constraint_exists(table: str, name: str) -> bool:
    insp = inspect(op.get_bind())
    return name in {c["name"] for c in insp.get_check_constraints(table)}


def upgrade() -> None:
    missing_column = not _column_exists("inventory_permissions", "role")
    missing_check = not _check_constraint_exists("inventory_permissions", _CONSTRAINT)
    if not missing_column and not missing_check:
        return
    with op.batch_alter_table("inventory_permissions") as batch_op:
        if missing_column:
            batch_op.add_column(
                sa.Column(
                    "role",
                    sa.String(length=16),
                    nullable=False,
                    server_default="manage",
                )
            )
        if missing_check:
            batch_op.create_check_constraint(
                _CONSTRAINT,
                "role IN ('manage', 'read')",
            )


def downgrade() -> None:
    has_column = _column_exists("inventory_permissions", "role")
    has_check = _check_constraint_exists("inventory_permissions", _CONSTRAINT)
    if not has_column and not has_check:
        return
    with op.batch_alter_table("inventory_permissions") as batch_op:
        if has_check:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
        if has_column:
            batch_op.drop_column("role")
