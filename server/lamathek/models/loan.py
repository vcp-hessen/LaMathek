from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base

LOAN_PHASE_DRAFT = "draft"
LOAN_PHASE_REVIEW = "review"
LOAN_PHASE_PACK = "pack"
LOAN_PHASE_HANDOVER = "handover"
LOAN_PHASE_RETURN = "return"
LOAN_PHASE_RESTOCK = "restock"
LOAN_PHASE_CLOSED = "closed"

WORKFLOW_LOAN_PHASES = frozenset(
    {
        LOAN_PHASE_REVIEW,
        LOAN_PHASE_PACK,
        LOAN_PHASE_HANDOVER,
        LOAN_PHASE_RETURN,
        LOAN_PHASE_RESTOCK,
    }
)

VALID_LOAN_PHASES = frozenset(
    {LOAN_PHASE_DRAFT, *WORKFLOW_LOAN_PHASES, LOAN_PHASE_CLOSED}
)


def is_workflow_loan_phase(phase: str) -> bool:
    return phase in WORKFLOW_LOAN_PHASES

LOAN_KIND_SHORT = "short"
LOAN_KIND_PERMANENT = "permanent"
VALID_LOAN_KINDS = frozenset({LOAN_KIND_SHORT, LOAN_KIND_PERMANENT})

LINE_STATUS_DRAFT = "draft"
LINE_STATUS_REQUESTED = "requested"
LINE_STATUS_CONFIRMED = "confirmed"
LINE_STATUS_PACKED = "packed"
LINE_STATUS_PICKED_UP = "picked_up"
LINE_STATUS_RETURN_REPORTED = "return_reported"
LINE_STATUS_RESTOCKED = "restocked"
LINE_STATUS_UNAVAILABLE = "unavailable"
LINE_STATUS_NOT_PACKED = "not_packed"
LINE_STATUS_NOT_PICKED_UP = "not_picked_up"
LINE_STATUS_NOT_RETURNED = "not_returned"
LINE_STATUS_WITHDRAWN = "withdrawn"

VALID_LINE_STATUSES = frozenset(
    {
        LINE_STATUS_DRAFT,
        LINE_STATUS_REQUESTED,
        LINE_STATUS_CONFIRMED,
        LINE_STATUS_PACKED,
        LINE_STATUS_PICKED_UP,
        LINE_STATUS_RETURN_REPORTED,
        LINE_STATUS_RESTOCKED,
        LINE_STATUS_UNAVAILABLE,
        LINE_STATUS_NOT_PACKED,
        LINE_STATUS_NOT_PICKED_UP,
        LINE_STATUS_NOT_RETURNED,
        LINE_STATUS_WITHDRAWN,
    }
)

LINE_STATUSES_BLOCKING = frozenset(
    {
        LINE_STATUS_CONFIRMED,
        LINE_STATUS_PACKED,
        LINE_STATUS_PICKED_UP,
        LINE_STATUS_RETURN_REPORTED,
    }
)

LINE_STATUSES_TERMINAL = frozenset(
    {
        LINE_STATUS_RESTOCKED,
        LINE_STATUS_UNAVAILABLE,
        LINE_STATUS_NOT_PACKED,
        LINE_STATUS_NOT_PICKED_UP,
        LINE_STATUS_NOT_RETURNED,
        LINE_STATUS_WITHDRAWN,
    }
)

ORIGIN_SET_ROLE_ASSIGNMENT = "assignment"
ORIGIN_SET_ROLE_OPTIONAL = "optional"
VALID_ORIGIN_SET_ROLES = frozenset(
    {ORIGIN_SET_ROLE_ASSIGNMENT, ORIGIN_SET_ROLE_OPTIONAL}
)

PHOTO_ROLE_PICKUP = "pickup"
PHOTO_ROLE_RETURN = "return"
VALID_LOAN_PHOTO_ROLES = frozenset({PHOTO_ROLE_PICKUP, PHOTO_ROLE_RETURN})


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
        CheckConstraint(
            "phase IN ('draft', 'review', 'pack', 'handover', 'return', 'restock', 'closed')",
            name="ck_loan_phase",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE")
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"))
    borrower_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    contact_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    phase: Mapped[str] = mapped_column(String(16), default=LOAN_PHASE_DRAFT)
    kind: Mapped[str] = mapped_column(String(16), default=LOAN_KIND_SHORT)
    wish_pickup_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    wish_return_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    pickup_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    return_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    pickup_note: Mapped[str] = mapped_column(Text(), default="", server_default="")
    return_note: Mapped[str] = mapped_column(Text(), default="", server_default="")
    mail_sent_borrower: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="0"
    )
    mail_sent_managers: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="0"
    )
    inventory: Mapped["Inventory"] = relationship(back_populates="loans")
    group: Mapped["Group"] = relationship()
    borrower_user: Mapped["User"] = relationship(foreign_keys=[borrower_user_id])
    contact_user: Mapped["User | None"] = relationship(foreign_keys=[contact_user_id])
    event: Mapped["Event | None"] = relationship()
    lines: Mapped[list["LoanLine"]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
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
    status: Mapped[str] = mapped_column(String(24), default=LINE_STATUS_DRAFT)
    status_before_end: Mapped[str | None] = mapped_column(String(24), nullable=True)
    note: Mapped[str] = mapped_column(Text(), default="", server_default="")
    reason: Mapped[str] = mapped_column(Text(), default="", server_default="")
    replaces_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_lines.id", ondelete="SET NULL"), nullable=True
    )
    split_from_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_lines.id", ondelete="SET NULL"), nullable=True
    )
    request_notified: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="0"
    )
    mail_pending: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="0"
    )
    returned_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    loan: Mapped["Loan"] = relationship(back_populates="lines")
    origin_set: Mapped["MaterialSet | None"] = relationship()
    piece: Mapped["Piece | None"] = relationship()
    material_type: Mapped["MaterialType | None"] = relationship()
    replaces_line: Mapped["LoanLine | None"] = relationship(
        remote_side="LoanLine.id",
        foreign_keys=[replaces_line_id],
    )
    split_from_line: Mapped["LoanLine | None"] = relationship(
        remote_side="LoanLine.id",
        foreign_keys=[split_from_line_id],
    )
