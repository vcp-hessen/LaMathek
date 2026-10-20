"""Datumsbasierte Verfügbarkeit (D0007): the only place that decides whether
material is free for a period.

A Verleih occupies its material from ``pickup_on`` to ``return_on`` (both days
inclusive; a Dauerleihgabe has no end). Only lines in LINE_STATUSES_BLOCKING
occupy anything; requests do not. Material that is physically out past its
return date occupies it up to today, so it cannot be handed out again now, while
later periods stay bookable (most things come back) and only get a warning.

Sets reserve nothing: a Set only describes what belongs together. Its pieces and
quantities are checked like any other line.

State that is not tied to dates still blocks everywhere: a retired piece, an
open total loss or an open severe damage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.loan import (
    LINE_STATUS_PICKED_UP,
    LINE_STATUS_RETURN_REPORTED,
    LINE_STATUSES_BLOCKING,
    LOAN_KIND_PERMANENT,
    Loan,
    LoanLine,
)
from lamathek.models.material import ITEM_STATUS_RETIRED, Piece
from lamathek.timezone import instance_today

# Physically with the Ausleihende*r: overdue lines keep blocking until restocked.
LINE_STATUSES_OUT = frozenset({LINE_STATUS_PICKED_UP, LINE_STATUS_RETURN_REPORTED})


@dataclass(frozen=True)
class Interval:
    """Closed date interval; ``end is None`` means open-ended (Dauerleihgabe)."""

    start: date
    end: date | None

    def overlaps(self, other: "Interval") -> bool:
        self_end = self.end or date.max
        other_end = other.end or date.max
        return self.start <= other_end and other.start <= self_end

    def contains(self, day: date) -> bool:
        return self.start <= day and (self.end is None or day <= self.end)


@dataclass
class Conflict:
    """Why material is not (or may not be) free; serialised into API errors and warnings."""

    code: str
    line_id: int | None = None
    piece_id: int | None = None
    material_type_id: int | None = None
    other_loan: Loan | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self, *, item_label: str | None = None) -> dict[str, Any]:
        """Always the full key set (``LoanWarning``); what does not apply is null."""
        other = self.other_loan
        title = None
        if other is not None:
            from lamathek.services.loan_display import loan_display_title

            title = loan_display_title(other)
        return {
            "code": self.code,
            "lineId": self.line_id,
            "pieceId": self.piece_id,
            "materialTypeId": self.material_type_id,
            "otherLoanId": other.id if other is not None else None,
            "otherLoanTitle": title,
            "otherInventoryId": other.inventory_id if other is not None else None,
            "itemLabel": item_label,
            "available": self.extra.get("available"),
            "occupied": self.extra.get("occupied"),
            "requested": self.extra.get("requested"),
        }


class AvailabilityError(ValueError):
    """Raised by the hard gates; the route answers 409 with the conflicts."""

    def __init__(self, code: str, conflicts: list[Conflict]):
        super().__init__(code)
        self.conflicts = conflicts

    def details(self) -> dict[str, Any]:
        return {"conflicts": [c.to_json() for c in self.conflicts]}


# --- Intervals -------------------------------------------------------------------


def loan_interval(loan: Loan, *, wish: bool = False) -> Interval | None:
    """The loan's period, or None while it has no start date (drafts)."""
    start = loan.wish_pickup_on if wish else loan.pickup_on
    end = loan.wish_return_on if wish else loan.return_on
    if start is None:
        return None
    if loan.kind == LOAN_KIND_PERMANENT:
        return Interval(start, None)
    return Interval(start, end if end is not None else start)


def line_interval(loan: Loan, line: LoanLine, *, today: date | None = None) -> Interval | None:
    base = loan_interval(loan)
    if base is None:
        return None
    if line.status in LINE_STATUSES_OUT and base.end is not None:
        today = today or instance_today()
        if base.end < today:
            return Interval(base.start, today)
    return base


def line_is_overdue(loan: Loan, line: LoanLine, *, today: date | None = None) -> bool:
    if line.status not in LINE_STATUSES_OUT or loan.kind == LOAN_KIND_PERMANENT:
        return False
    return loan.return_on is not None and loan.return_on < (today or instance_today())


# --- Queries ---------------------------------------------------------------------


def _lines(
    session: Session,
    *,
    statuses: Iterable[str],
    piece_id: int | None = None,
    material_type_id: int | None = None,
    stock_variant: str | None = None,
    exclude_line_ids: Iterable[int] = (),
) -> list[tuple[Loan, LoanLine]]:
    stmt = (
        select(LoanLine, Loan)
        .join(Loan, LoanLine.loan_id == Loan.id)
        .where(LoanLine.status.in_(tuple(statuses)))
        .options(selectinload(Loan.group), selectinload(Loan.event))
    )
    if piece_id is not None:
        stmt = stmt.where(LoanLine.piece_id == piece_id)
    if material_type_id is not None:
        stmt = stmt.where(LoanLine.material_type_id == material_type_id)
    if stock_variant is not None:
        stmt = stmt.where(LoanLine.stock_variant == stock_variant)
    excluded = tuple(exclude_line_ids)
    if excluded:
        stmt = stmt.where(LoanLine.id.not_in(excluded))
    return [(loan, line) for line, loan in session.execute(stmt).all()]


def overlapping_blocking_lines(
    session: Session,
    interval: Interval,
    *,
    piece_id: int | None = None,
    material_type_id: int | None = None,
    stock_variant: str | None = None,
    exclude_line_ids: Iterable[int] = (),
    today: date | None = None,
) -> list[tuple[Loan, LoanLine, Interval]]:
    today = today or instance_today()
    found = []
    for loan, line in _lines(
        session,
        statuses=LINE_STATUSES_BLOCKING,
        piece_id=piece_id,
        material_type_id=material_type_id,
        stock_variant=stock_variant,
        exclude_line_ids=exclude_line_ids,
    ):
        occupied = line_interval(loan, line, today=today)
        if occupied is not None and occupied.overlaps(interval):
            found.append((loan, line, occupied))
    return found


def available_stock_quantity(
    session: Session, material_type_id: int, stock_variant: str | None = None
) -> int:
    """Stock that can be lent at all (active lots minus open losses), per combination (#12)."""
    from lamathek.services.stock_losses import available_stock_quantity as available

    return available(session, material_type_id, stock_variant)


def stock_peak(
    session: Session,
    material_type_id: int,
    interval: Interval,
    *,
    stock_variant: str | None = None,
    exclude_line_ids: Iterable[int] = (),
    today: date | None = None,
) -> int:
    """Highest quantity of this Materialart (and combination) occupied on any day of ``interval``."""
    occupied = overlapping_blocking_lines(
        session,
        interval,
        material_type_id=material_type_id,
        stock_variant=stock_variant,
        exclude_line_ids=exclude_line_ids,
        today=today,
    )
    if not occupied:
        return 0
    # Demand only rises where some period starts, so the peak lies on one of these days.
    candidates = {interval.start} | {
        span.start for _, _, span in occupied if interval.contains(span.start)
    }
    return max(
        sum(line.quantity or 0 for _, line, span in occupied if span.contains(day))
        for day in candidates
    )


# --- Checks ----------------------------------------------------------------------


def piece_state_conflicts(session: Session, piece: Piece) -> list[Conflict]:
    """Date-independent reasons a piece cannot go out at all."""
    from lamathek.services.piece_availability import (
        piece_has_open_severe_damage,
        piece_has_open_total_loss,
    )

    if piece.status == ITEM_STATUS_RETIRED:
        return [Conflict("piece_retired", piece_id=piece.id)]
    if piece_has_open_total_loss(session, piece.id):
        return [Conflict("piece_total_loss", piece_id=piece.id)]
    if piece_has_open_severe_damage(session, piece.id):
        return [Conflict("piece_severe_damage", piece_id=piece.id)]
    return []


def piece_conflicts(
    session: Session,
    piece_id: int,
    interval: Interval,
    *,
    exclude_line_ids: Iterable[int] = (),
    line_id: int | None = None,
) -> list[Conflict]:
    piece = session.get(Piece, piece_id)
    if piece is None:
        return [Conflict("invalid_piece", piece_id=piece_id)]
    conflicts = piece_state_conflicts(session, piece)
    for loan, line, _span in overlapping_blocking_lines(
        session, interval, piece_id=piece_id, exclude_line_ids=exclude_line_ids
    ):
        conflicts.append(
            Conflict(
                "piece_overdue" if line_is_overdue(loan, line) else "piece_booked",
                line_id=line_id,
                piece_id=piece_id,
                other_loan=loan,
            )
        )
    for conflict in conflicts:
        conflict.line_id = line_id
    return conflicts


def stock_conflicts(
    session: Session,
    material_type_id: int,
    quantity: int,
    interval: Interval,
    *,
    stock_variant: str = "{}",
    exclude_line_ids: Iterable[int] = (),
    line_id: int | None = None,
) -> list[Conflict]:
    available = available_stock_quantity(session, material_type_id, stock_variant)
    peak = stock_peak(
        session,
        material_type_id,
        interval,
        stock_variant=stock_variant,
        exclude_line_ids=exclude_line_ids,
    )
    if peak + quantity <= available:
        return []
    return [
        Conflict(
            "stock_short",
            line_id=line_id,
            material_type_id=material_type_id,
            extra={"available": available, "occupied": peak, "requested": quantity},
        )
    ]


def line_conflicts(
    session: Session, loan: Loan, line: LoanLine, *, interval: Interval | None = None
) -> list[Conflict]:
    """Conflicts if ``line`` were to occupy ``interval`` (default: the loan's period)."""
    interval = interval or loan_interval(loan)
    if interval is None:
        return [Conflict("pickup_required", line_id=line.id)]
    exclude = (line.id,) if line.id is not None else ()
    if line.piece_id is not None:
        return piece_conflicts(
            session, line.piece_id, interval, exclude_line_ids=exclude, line_id=line.id
        )
    if line.material_type_id is not None and line.quantity:
        return stock_conflicts(
            session,
            line.material_type_id,
            line.quantity,
            interval,
            stock_variant=line.stock_variant or "{}",
            exclude_line_ids=exclude,
            line_id=line.id,
        )
    return []


def assert_line_available(
    session: Session, loan: Loan, line: LoanLine, *, interval: Interval | None = None
) -> None:
    """Hard gate before a line starts occupying material (confirm, replace, restore)."""
    conflicts = line_conflicts(session, loan, line, interval=interval)
    if not conflicts:
        return
    code = "over_loaned" if line.piece_id is None else "piece_unavailable"
    raise AvailabilityError(code, conflicts)


def assert_loan_lines_available(session: Session, loan: Loan) -> None:
    """After a date change: every occupying line must still fit its new period."""
    conflicts: list[Conflict] = []
    for line in loan.lines:
        if line.status not in LINE_STATUSES_BLOCKING:
            continue
        interval = line_interval(loan, line)
        if interval is None:
            raise ValueError("pickup_required")
        conflicts.extend(line_conflicts(session, loan, line, interval=interval))
    if conflicts:
        raise AvailabilityError("dates_conflict", conflicts)


def stock_occupied_from(
    session: Session,
    material_type_id: int,
    day: date,
    *,
    stock_variant: str | None = None,
    exclude_line_ids: Iterable[int] = (),
) -> int:
    """Peak quantity occupied from ``day`` on (floor for lowering stock by hand)."""
    return stock_peak(
        session,
        material_type_id,
        Interval(day, None),
        stock_variant=stock_variant,
        exclude_line_ids=exclude_line_ids,
    )
