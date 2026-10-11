from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base

LOAN_STATUS_PLANNED = "planned"
LOAN_STATUS_HANDED_OUT = "handed_out"
LOAN_STATUS_CLOSED = "closed"
VALID_LOAN_STATUSES = frozenset(
    {LOAN_STATUS_PLANNED, LOAN_STATUS_HANDED_OUT, LOAN_STATUS_CLOSED}
)

RETURN_OUTCOME_RETURNED = "returned"
RETURN_OUTCOME_LOSS = "loss"
VALID_RETURN_OUTCOMES = frozenset({RETURN_OUTCOME_RETURNED, RETURN_OUTCOME_LOSS})

LOAN_KIND_SHORT = "short"
LOAN_KIND_PERMANENT = "permanent"
VALID_LOAN_KINDS = frozenset({LOAN_KIND_SHORT, LOAN_KIND_PERMANENT})

ORIGIN_SET_ROLE_ASSIGNMENT = "assignment"
ORIGIN_SET_ROLE_OPTIONAL = "optional"
VALID_ORIGIN_SET_ROLES = frozenset(
    {ORIGIN_SET_ROLE_ASSIGNMENT, ORIGIN_SET_ROLE_OPTIONAL}
)


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("name", name="uq_group_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("name", name="uq_event_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('short', 'permanent')",
            name="ck_loan_kind",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE")
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"))
    responsible_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default=LOAN_STATUS_PLANNED)
    kind: Mapped[str] = mapped_column(String(16), default=LOAN_KIND_SHORT)
    starts_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date(), nullable=True)

    inventory: Mapped["Inventory"] = relationship(back_populates="loans")
    group: Mapped["Group"] = relationship()
    responsible_user: Mapped["User"] = relationship()
    event: Mapped["Event | None"] = relationship()
    lines: Mapped[list["LoanLine"]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
    )
    returns: Mapped[list["LoanReturn"]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="LoanReturn.id",
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order",
    )


class LoanLine(Base):
    __tablename__ = "loan_lines"
    __table_args__ = (
        CheckConstraint(
            "("
            "(piece_id IS NOT NULL AND material_type_id IS NULL AND quantity IS NULL) OR "
            "(piece_id IS NULL AND material_type_id IS NOT NULL AND quantity IS NOT NULL AND quantity > 0)"
            ")",
            name="ck_loan_line_kind",
        ),
        CheckConstraint(
            "(origin_set_role IS NULL) OR (origin_set_role IN ('assignment', 'optional'))",
            name="ck_loan_line_origin_role",
        ),
        UniqueConstraint("loan_id", "piece_id", name="uq_loan_line_piece"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"))
    piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("pieces.id", ondelete="CASCADE"), nullable=True
    )
    material_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("material_types.id", ondelete="CASCADE"), nullable=True
    )
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_set_id: Mapped[int | None] = mapped_column(
        ForeignKey("sets.id", ondelete="SET NULL"), nullable=True
    )
    origin_set_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_set_role: Mapped[str | None] = mapped_column(String(16), nullable=True)

    loan: Mapped["Loan"] = relationship(back_populates="lines")
    origin_set: Mapped["MaterialSet | None"] = relationship()
    piece: Mapped["Piece | None"] = relationship()
    material_type: Mapped["MaterialType | None"] = relationship()
    return_lines: Mapped[list["LoanReturnLine"]] = relationship(
        back_populates="loan_line",
        cascade="all, delete-orphan",
    )


class LoanReturn(Base):
    __tablename__ = "loan_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"))
    recorded_on: Mapped[date] = mapped_column(Date())

    loan: Mapped["Loan"] = relationship(back_populates="returns")
    lines: Mapped[list["LoanReturnLine"]] = relationship(
        back_populates="loan_return",
        cascade="all, delete-orphan",
    )


class LoanReturnLine(Base):
    __tablename__ = "loan_return_lines"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('returned', 'loss')",
            name="ck_loan_return_line_outcome",
        ),
        CheckConstraint(
            "(quantity IS NULL) OR (quantity > 0)",
            name="ck_loan_return_line_quantity_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_return_id: Mapped[int] = mapped_column(
        ForeignKey("loan_returns.id", ondelete="CASCADE")
    )
    loan_line_id: Mapped[int] = mapped_column(
        ForeignKey("loan_lines.id", ondelete="CASCADE")
    )
    outcome: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    loan_return: Mapped["LoanReturn"] = relationship(back_populates="lines")
    loan_line: Mapped["LoanLine"] = relationship(back_populates="return_lines")
