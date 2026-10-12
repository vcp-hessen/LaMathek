"""piece and stock lot metadata; manufacturer on material type

Revision ID: 20261012_0020
Revises: 20261011_0019
Create Date: 2026-10-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261012_0020"
down_revision: Union[str, None] = "20261011_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def _check_constraint_exists(table: str, name: str) -> bool:
    insp = inspect(op.get_bind())
    return name in {c["name"] for c in insp.get_check_constraints(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def _upgrade_item_table(table: str) -> None:
    constraint_name = f"ck_{table}_status"
    column_specs: list[tuple[str, sa.Column]] = [
        ("acquired_year", sa.Column("acquired_year", sa.Integer(), nullable=True)),
        ("note", sa.Column("note", sa.Text(), nullable=True)),
        ("source", sa.Column("source", sa.Text(), nullable=True)),
        (
            "status",
            sa.Column(
                "status",
                sa.String(length=16),
                server_default="active",
                nullable=False,
            ),
        ),
        (
            "serial_number",
            sa.Column("serial_number", sa.String(length=255), nullable=True),
        ),
        ("new_value_cents", sa.Column("new_value_cents", sa.Integer(), nullable=True)),
    ]
    missing = [name for name, _ in column_specs if not _column_exists(table, name)]
    need_constraint = not _check_constraint_exists(table, constraint_name)
    if not missing and not need_constraint:
        return

    with op.batch_alter_table(table) as batch_op:
        for name in missing:
            col = next(col for n, col in column_specs if n == name)
            batch_op.add_column(col)
        if need_constraint:
            batch_op.create_check_constraint(
                constraint_name,
                "status IN ('active', 'retired')",
            )


def upgrade() -> None:
    _add_column_if_missing(
        "material_types",
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
    )
    _add_column_if_missing(
        "material_types",
        sa.Column("model_name", sa.String(length=255), nullable=True),
    )

    for table in ("pieces", "stock_lots"):
        _upgrade_item_table(table)


def downgrade() -> None:
    for table in ("pieces", "stock_lots"):
        constraint_name = f"ck_{table}_status"
        columns = (
            "new_value_cents",
            "serial_number",
            "status",
            "source",
            "note",
            "acquired_year",
        )
        has_constraint = _check_constraint_exists(table, constraint_name)
        to_drop = [c for c in columns if _column_exists(table, c)]
        if not has_constraint and not to_drop:
            continue
        with op.batch_alter_table(table) as batch_op:
            if has_constraint:
                batch_op.drop_constraint(constraint_name, type_="check")
            for column in to_drop:
                batch_op.drop_column(column)

    if _column_exists("material_types", "model_name"):
        op.drop_column("material_types", "model_name")
    if _column_exists("material_types", "manufacturer"):
        op.drop_column("material_types", "manufacturer")
