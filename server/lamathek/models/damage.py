from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base


class Damage(Base):
    __tablename__ = "damages"

    id: Mapped[int] = mapped_column(primary_key=True)
    piece_id: Mapped[int] = mapped_column(
        ForeignKey("pieces.id", ondelete="CASCADE")
    )
    recorded_on: Mapped[date] = mapped_column(Date())
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    severe: Mapped[bool] = mapped_column(Boolean(), default=False)

    piece: Mapped["Piece"] = relationship(back_populates="damages")
    repair: Mapped["Repair | None"] = relationship(
        back_populates="damage",
        uselist=False,
        cascade="all, delete-orphan",
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="damage",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
    )


class Repair(Base):
    __tablename__ = "repairs"
    __table_args__ = (UniqueConstraint("damage_id", name="uq_repair_per_damage"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    damage_id: Mapped[int] = mapped_column(
        ForeignKey("damages.id", ondelete="CASCADE")
    )
    recorded_on: Mapped[date] = mapped_column(Date())
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)

    damage: Mapped["Damage"] = relationship(back_populates="repair")
