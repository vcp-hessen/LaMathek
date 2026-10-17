from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN piece_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN stock_lot_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN set_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN material_type_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN damage_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN inventory_id IS NOT NULL THEN 1 ELSE 0 END)"
            "+ (CASE WHEN loan_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_photo_single_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("pieces.id", ondelete="CASCADE"), nullable=True
    )
    stock_lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_lots.id", ondelete="CASCADE"), nullable=True
    )
    set_id: Mapped[int | None] = mapped_column(
        ForeignKey("sets.id", ondelete="CASCADE"), nullable=True
    )
    material_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE"), nullable=True
    )
    damage_id: Mapped[int | None] = mapped_column(
        ForeignKey("damages.id", ondelete="CASCADE"), nullable=True
    )
    inventory_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE"), nullable=True
    )
    loan_id: Mapped[int | None] = mapped_column(
        ForeignKey("loans.id", ondelete="CASCADE"), nullable=True
    )
    loan_photo_role: Mapped[str | None] = mapped_column(String(16), nullable=True)

    piece: Mapped["Piece | None"] = relationship(back_populates="photos")
    stock_lot: Mapped["StockLot | None"] = relationship(back_populates="photos")
    material_set: Mapped["MaterialSet | None"] = relationship(back_populates="photos")
    material_type: Mapped["MaterialType | None"] = relationship(back_populates="photos")
    damage: Mapped["Damage | None"] = relationship(back_populates="photos")
    inventory: Mapped["Inventory | None"] = relationship(back_populates="photos")
    loan: Mapped["Loan | None"] = relationship(back_populates="photos")


def _delete_photo_files(_mapper, _connection, target: Photo) -> None:
    from lamathek.services.photo_storage import delete_photo_files

    delete_photo_files(target.id)


event.listen(Photo, "before_delete", _delete_photo_files)
