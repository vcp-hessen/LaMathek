"""multiple variant dimensions per material type

Revision ID: 20261011_0016
Revises: 20261010_0015
Create Date: 2026-10-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261011_0016"
down_revision: Union[str, None] = "20261010_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _table_exists("material_type_variants"):
        op.create_table(
            "material_type_variants",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("material_type_id", sa.Integer(), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(
                ["material_type_id"], ["material_types.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "material_type_id",
                "label",
                name="uq_material_type_variant_label",
            ),
        )

    if _column_exists("material_types", "variant_label"):
        op.execute(
            """
            INSERT INTO material_type_variants (material_type_id, label, sort_order)
            SELECT mt.id, mt.variant_label, 0
            FROM material_types mt
            WHERE mt.variant_label IS NOT NULL AND TRIM(mt.variant_label) != ''
            AND NOT EXISTS (
                SELECT 1 FROM material_type_variants v
                WHERE v.material_type_id = mt.id AND v.label = mt.variant_label
            )
            """
        )

    if _column_exists("material_type_variant_values", "material_type_id"):
        if not _column_exists("material_type_variant_values", "variant_id"):
            with op.batch_alter_table("material_type_variant_values") as batch_op:
                batch_op.add_column(sa.Column("variant_id", sa.Integer(), nullable=True))

        op.execute(
            """
            UPDATE material_type_variant_values
            SET variant_id = (
                SELECT v.id FROM material_type_variants v
                WHERE v.material_type_id = material_type_variant_values.material_type_id
                LIMIT 1
            )
            WHERE variant_id IS NULL
            """
        )

        op.execute("DELETE FROM material_type_variant_values WHERE variant_id IS NULL")

        op.create_table(
            "material_type_variant_values_new",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("variant_id", sa.Integer(), nullable=False),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(
                ["variant_id"], ["material_type_variants.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("variant_id", "value", name="uq_material_type_variant_value"),
        )
        op.execute(
            """
            INSERT INTO material_type_variant_values_new (id, variant_id, sort_order, value)
            SELECT id, variant_id, sort_order, value
            FROM material_type_variant_values
            """
        )
        op.drop_table("material_type_variant_values")
        op.rename_table("material_type_variant_values_new", "material_type_variant_values")

    if not _table_exists("piece_variant_values"):
        op.create_table(
            "piece_variant_values",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("piece_id", sa.Integer(), nullable=False),
            sa.Column("variant_id", sa.Integer(), nullable=False),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(["piece_id"], ["pieces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["variant_id"], ["material_type_variants.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("piece_id", "variant_id", name="uq_piece_variant_value"),
        )

    if _column_exists("pieces", "variant"):
        op.execute(
            """
            INSERT INTO piece_variant_values (piece_id, variant_id, value)
            SELECT p.id, v.id, p.variant
            FROM pieces p
            JOIN material_type_variants v ON v.material_type_id = p.material_type_id
            WHERE p.variant IS NOT NULL AND TRIM(p.variant) != ''
            AND NOT EXISTS (
                SELECT 1 FROM piece_variant_values pv WHERE pv.piece_id = p.id
            )
            """
        )

    if not _table_exists("stock_lot_variant_values"):
        op.create_table(
            "stock_lot_variant_values",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_lot_id", sa.Integer(), nullable=False),
            sa.Column("variant_id", sa.Integer(), nullable=False),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(["stock_lot_id"], ["stock_lots.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["variant_id"], ["material_type_variants.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "stock_lot_id", "variant_id", name="uq_stock_lot_variant_value"
            ),
        )

    if _column_exists("stock_lots", "variant"):
        op.execute(
            """
            INSERT INTO stock_lot_variant_values (stock_lot_id, variant_id, value)
            SELECT l.id, v.id, l.variant
            FROM stock_lots l
            JOIN material_type_variants v ON v.material_type_id = l.material_type_id
            WHERE l.variant IS NOT NULL AND TRIM(l.variant) != ''
            AND NOT EXISTS (
                SELECT 1 FROM stock_lot_variant_values slv WHERE slv.stock_lot_id = l.id
            )
            """
        )

    if _column_exists("pieces", "variant"):
        with op.batch_alter_table("pieces") as batch_op:
            batch_op.drop_column("variant")

    if _column_exists("stock_lots", "variant"):
        with op.batch_alter_table("stock_lots") as batch_op:
            batch_op.drop_column("variant")

    if _column_exists("material_types", "variant_label"):
        with op.batch_alter_table("material_types") as batch_op:
            batch_op.drop_column("variant_label")


def downgrade() -> None:
    with op.batch_alter_table("material_types") as batch_op:
        batch_op.add_column(sa.Column("variant_label", sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE material_types
        SET variant_label = (
            SELECT v.label FROM material_type_variants v
            WHERE v.material_type_id = material_types.id
            ORDER BY v.sort_order, v.id
            LIMIT 1
        )
        """
    )

    with op.batch_alter_table("stock_lots") as batch_op:
        batch_op.add_column(sa.Column("variant", sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE stock_lots
        SET variant = (
            SELECT slv.value FROM stock_lot_variant_values slv
            WHERE slv.stock_lot_id = stock_lots.id
            LIMIT 1
        )
        """
    )

    with op.batch_alter_table("pieces") as batch_op:
        batch_op.add_column(sa.Column("variant", sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE pieces
        SET variant = (
            SELECT pv.value FROM piece_variant_values pv
            WHERE pv.piece_id = pieces.id
            LIMIT 1
        )
        """
    )

    op.drop_table("stock_lot_variant_values")
    op.drop_table("piece_variant_values")

    with op.batch_alter_table("material_type_variant_values") as batch_op:
        batch_op.add_column(sa.Column("material_type_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE material_type_variant_values
        SET material_type_id = (
            SELECT v.material_type_id FROM material_type_variants v
            WHERE v.id = material_type_variant_values.variant_id
        )
        """
    )

    with op.batch_alter_table("material_type_variant_values") as batch_op:
        batch_op.drop_constraint("material_type_variant_values_variant_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("uq_material_type_variant_value", type_="unique")
        batch_op.drop_column("variant_id")
        batch_op.alter_column("material_type_id", nullable=False)
        batch_op.create_foreign_key(
            "material_type_variant_values_material_type_id_fkey",
            "material_types",
            ["material_type_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_material_type_variant_value",
            ["material_type_id", "value"],
        )

    op.drop_table("material_type_variants")
