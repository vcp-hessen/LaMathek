from sqlalchemy import CheckConstraint, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base

INVENTORY_VISIBILITY_INTERNAL = "internal"
INVENTORY_VISIBILITY_ACTIVE = "active"
INVENTORY_VISIBILITY_ARCHIVED = "archived"
VALID_INVENTORY_VISIBILITIES = frozenset(
    {
        INVENTORY_VISIBILITY_INTERNAL,
        INVENTORY_VISIBILITY_ACTIVE,
        INVENTORY_VISIBILITY_ARCHIVED,
    }
)


class Inventory(Base):
    __tablename__ = "inventories"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('internal', 'active', 'archived')",
            name="ck_inventory_visibility",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    visibility: Mapped[str] = mapped_column(
        String(16), default=INVENTORY_VISIBILITY_INTERNAL
    )
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
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
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
