from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base

DAMAGE_KIND_DAMAGE = "damage"
DAMAGE_KIND_TOTAL_LOSS = "total_loss"
VALID_DAMAGE_KINDS = frozenset({DAMAGE_KIND_DAMAGE, DAMAGE_KIND_TOTAL_LOSS})

RESOLUTION_REPAIRED = "repaired"
RESOLUTION_FOUND_AGAIN = "found_again"
RESOLUTION_CANCELLED_MISTAKE = "cancelled_mistake"
VALID_RESOLUTION_KINDS = frozenset(
    {RESOLUTION_REPAIRED, RESOLUTION_FOUND_AGAIN, RESOLUTION_CANCELLED_MISTAKE}
)


class Damage(Base):
    __tablename__ = "damages"

    id: Mapped[int] = mapped_column(primary_key=True)
    piece_id: Mapped[int] = mapped_column(
        ForeignKey("pieces.id", ondelete="CASCADE")
    )
    recorded_on: Mapped[date] = mapped_column(Date())
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    severe: Mapped[bool] = mapped_column(Boolean(), default=False)
    kind: Mapped[str] = mapped_column(String(16), default=DAMAGE_KIND_DAMAGE)
    loan_id: Mapped[int | None] = mapped_column(
        ForeignKey("loans.id", ondelete="SET NULL"), nullable=True
    )
    loan_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_lines.id", ondelete="SET NULL"), nullable=True
    )

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
    resolution_kind: Mapped[str] = mapped_column(String(24), default=RESOLUTION_REPAIRED)

    damage: Mapped["Damage"] = relationship(back_populates="repair")
