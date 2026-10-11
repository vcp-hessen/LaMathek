from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base

SET_ROLE_ASSIGNMENT = "assignment"
SET_ROLE_OPTIONAL = "optional"
VALID_SET_ROLES = frozenset({SET_ROLE_ASSIGNMENT, SET_ROLE_OPTIONAL})


class MaterialSet(Base):
    __tablename__ = "sets"
    __table_args__ = (
        UniqueConstraint("inventory_id", "name", name="uq_set_per_inventory"),
        UniqueConstraint(
            "inventory_id",
            "short_name",
            name="uq_set_short_name_per_inventory",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    inventory: Mapped["Inventory"] = relationship(back_populates="sets")
    stock_lines: Mapped[list["SetStockLine"]] = relationship(
        back_populates="material_set",
        cascade="all, delete-orphan",
    )
    pieces: Mapped[list["Piece"]] = relationship(back_populates="material_set")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="material_set",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
    )


class SetStockLine(Base):
    __tablename__ = "set_stock_lines"
    __table_args__ = (
        UniqueConstraint(
            "set_id",
            "material_type_id",
            "role",
            name="uq_set_stock_line",
        ),
        CheckConstraint("quantity > 0", name="ck_set_stock_line_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("sets.id", ondelete="CASCADE"))
    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)

    material_set: Mapped["MaterialSet"] = relationship(back_populates="stock_lines")
    material_type: Mapped["MaterialType"] = relationship()
