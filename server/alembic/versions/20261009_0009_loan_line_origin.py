"""loan lines from set origin, no set lines

Revision ID: 20261009_0009
Revises: 20261009_0008
Create Date: 2026-10-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0009"
down_revision: Union[str, None] = "20261009_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_set_lines(connection) -> None:
    set_lines = connection.execute(
        sa.text(
            "SELECT id, loan_id, set_id FROM loan_lines WHERE set_id IS NOT NULL"
        )
    ).fetchall()
    for row in set_lines:
        line_id, loan_id, set_id = row[0], row[1], row[2]
        set_row = connection.execute(
            sa.text("SELECT name FROM sets WHERE id = :sid"),
            {"sid": set_id},
        ).fetchone()
        set_name = set_row[0] if set_row else ""

        pieces = connection.execute(
            sa.text(
                "SELECT id FROM pieces WHERE set_id = :sid AND set_role = 'assignment'"
            ),
            {"sid": set_id},
        ).fetchall()
        for (piece_id,) in pieces:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO loan_lines
                    (loan_id, piece_id, material_type_id, quantity,
                     origin_set_id, origin_set_name, origin_set_role)
                    VALUES (:loan_id, :piece_id, NULL, NULL,
                            :set_id, :set_name, 'assignment')
                    """
                ),
                {
                    "loan_id": loan_id,
                    "piece_id": piece_id,
                    "set_id": set_id,
                    "set_name": set_name,
                },
            )

        stock_rows = connection.execute(
            sa.text(
                """
                SELECT material_type_id, quantity FROM set_stock_lines
                WHERE set_id = :sid AND role = 'assignment'
                """
            ),
            {"sid": set_id},
        ).fetchall()
        for material_type_id, quantity in stock_rows:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO loan_lines
                    (loan_id, piece_id, material_type_id, quantity,
                     origin_set_id, origin_set_name, origin_set_role)
                    VALUES (:loan_id, NULL, :mt_id, :qty,
                            :set_id, :set_name, 'assignment')
                    """
                ),
                {
                    "loan_id": loan_id,
                    "mt_id": material_type_id,
                    "qty": quantity,
                    "set_id": set_id,
                    "set_name": set_name,
                },
            )

        connection.execute(
            sa.text("DELETE FROM loan_lines WHERE id = :lid"),
            {"lid": line_id},
        )


def upgrade() -> None:
    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.add_column(sa.Column("origin_set_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("origin_set_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("origin_set_role", sa.String(length=16), nullable=True))

    _migrate_set_lines(op.get_bind())

    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.create_foreign_key(
            "fk_loan_line_origin_set",
            "sets",
            ["origin_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_constraint("uq_loan_line_set", type_="unique")
        batch_op.drop_constraint("uq_loan_line_stock", type_="unique")
        batch_op.drop_constraint("ck_loan_line_kind", type_="check")
        batch_op.drop_column("set_id")
        batch_op.create_check_constraint(
            "ck_loan_line_kind",
            "("
            "(piece_id IS NOT NULL AND material_type_id IS NULL AND quantity IS NULL) OR "
            "(piece_id IS NULL AND material_type_id IS NOT NULL AND quantity IS NOT NULL AND quantity > 0)"
            ")",
        )
        batch_op.create_check_constraint(
            "ck_loan_line_origin_role",
            "(origin_set_role IS NULL) OR (origin_set_role IN ('assignment', 'optional'))",
        )


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported")
