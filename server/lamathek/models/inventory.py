from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    permissions: Mapped[list["InventoryPermission"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    material_types: Mapped[list["MaterialType"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    sets: Mapped[list["MaterialSet"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
    )


class InventoryPermission(Base):
    __tablename__ = "inventory_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "inventory_id", name="uq_inventory_permission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE")
    )

    inventory: Mapped["Inventory"] = relationship(back_populates="permissions")
