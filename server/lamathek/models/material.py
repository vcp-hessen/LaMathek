from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base

TRACKING_PIECE = "piece"
TRACKING_STOCK = "stock"
VALID_TRACKING = frozenset({TRACKING_PIECE, TRACKING_STOCK})


class MaterialType(Base):
    __tablename__ = "material_types"
    __table_args__ = (
        UniqueConstraint("inventory_id", "name", name="uq_material_type_per_inventory"),
        UniqueConstraint(
            "inventory_id",
            "short_name",
            name="uq_material_type_short_name_per_inventory",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    tracking: Mapped[str] = mapped_column(String(16))
    variant_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consumable: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="0")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    inventory: Mapped["Inventory"] = relationship(back_populates="material_types")
    category: Mapped["Category | None"] = relationship(back_populates="material_types")
    variant_values: Mapped[list["MaterialTypeVariantValue"]] = relationship(
        back_populates="material_type",
        cascade="all, delete-orphan",
        order_by="MaterialTypeVariantValue.sort_order",
    )
    pieces: Mapped[list["Piece"]] = relationship(
        back_populates="material_type",
        cascade="all, delete-orphan",
    )
    stock_lots: Mapped[list["StockLot"]] = relationship(
        back_populates="material_type",
        cascade="all, delete-orphan",
        order_by="StockLot.id",
    )


class MaterialTypeVariantValue(Base):
    __tablename__ = "material_type_variant_values"
    __table_args__ = (
        UniqueConstraint(
            "material_type_id",
            "value",
            name="uq_material_type_variant_value",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE")
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    value: Mapped[str] = mapped_column(String(255))

    material_type: Mapped["MaterialType"] = relationship(back_populates="variant_values")


class Piece(Base):
    __tablename__ = "pieces"
    __table_args__ = (
        CheckConstraint(
            "(set_id IS NULL AND set_role IS NULL) OR "
            "(set_id IS NOT NULL AND set_role IS NOT NULL)",
            name="ck_piece_set_membership",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    variant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    set_id: Mapped[int | None] = mapped_column(
        ForeignKey("sets.id", ondelete="SET NULL"), nullable=True
    )
    set_role: Mapped[str | None] = mapped_column(String(16), nullable=True)

    material_type: Mapped["MaterialType"] = relationship(back_populates="pieces")
    material_set: Mapped["MaterialSet | None"] = relationship(back_populates="pieces")
    damages: Mapped[list["Damage"]] = relationship(
        back_populates="piece",
        cascade="all, delete-orphan",
        order_by="Damage.id",
    )


class StockLot(Base):
    __tablename__ = "stock_lots"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_stock_lot_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE")
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    material_type: Mapped["MaterialType"] = relationship(back_populates="stock_lots")
