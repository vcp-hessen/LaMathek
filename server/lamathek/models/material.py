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
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consumable: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="0")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    inventory: Mapped["Inventory"] = relationship(back_populates="material_types")
    category: Mapped["Category | None"] = relationship(back_populates="material_types")
    variants: Mapped[list["MaterialTypeVariant"]] = relationship(
        back_populates="material_type",
        cascade="all, delete-orphan",
        order_by="MaterialTypeVariant.sort_order",
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
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="material_type",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
    )


class MaterialTypeVariant(Base):
    __tablename__ = "material_type_variants"
    __table_args__ = (
        UniqueConstraint(
            "material_type_id",
            "label",
            name="uq_material_type_variant_label",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    material_type: Mapped["MaterialType"] = relationship(back_populates="variants")
    values: Mapped[list["MaterialTypeVariantValue"]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="MaterialTypeVariantValue.sort_order",
    )


class MaterialTypeVariantValue(Base):
    __tablename__ = "material_type_variant_values"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "value",
            name="uq_material_type_variant_value",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("material_type_variants.id", ondelete="CASCADE")
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    value: Mapped[str] = mapped_column(String(255))

    variant: Mapped["MaterialTypeVariant"] = relationship(back_populates="values")


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
    set_id: Mapped[int | None] = mapped_column(
        ForeignKey("sets.id", ondelete="SET NULL"), nullable=True
    )
    set_role: Mapped[str | None] = mapped_column(String(16), nullable=True)

    material_type: Mapped["MaterialType"] = relationship(back_populates="pieces")
    material_set: Mapped["MaterialSet | None"] = relationship(back_populates="pieces")
    variant_selections: Mapped[list["PieceVariantValue"]] = relationship(
        back_populates="piece",
        cascade="all, delete-orphan",
    )
    damages: Mapped[list["Damage"]] = relationship(
        back_populates="piece",
        cascade="all, delete-orphan",
        order_by="Damage.id",
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="piece",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
    )


class PieceVariantValue(Base):
    __tablename__ = "piece_variant_values"
    __table_args__ = (
        UniqueConstraint("piece_id", "variant_id", name="uq_piece_variant_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    piece_id: Mapped[int] = mapped_column(ForeignKey("pieces.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("material_type_variants.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(String(255))

    piece: Mapped["Piece"] = relationship(back_populates="variant_selections")
    variant: Mapped["MaterialTypeVariant"] = relationship()


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
    quantity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    material_type: Mapped["MaterialType"] = relationship(back_populates="stock_lots")
    variant_selections: Mapped[list["StockLotVariantValue"]] = relationship(
        back_populates="stock_lot",
        cascade="all, delete-orphan",
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="stock_lot",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
    )


class StockLotVariantValue(Base):
    __tablename__ = "stock_lot_variant_values"
    __table_args__ = (
        UniqueConstraint("stock_lot_id", "variant_id", name="uq_stock_lot_variant_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_lot_id: Mapped[int] = mapped_column(
        ForeignKey("stock_lots.id", ondelete="CASCADE")
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("material_type_variants.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(String(255))

    stock_lot: Mapped["StockLot"] = relationship(back_populates="variant_selections")
    variant: Mapped["MaterialTypeVariant"] = relationship()
