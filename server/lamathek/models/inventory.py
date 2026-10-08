from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    permissions: Mapped[list["InventoryPermission"]] = relationship(
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
