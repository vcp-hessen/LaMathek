"""Warnungen zu Belegung und Stück-Ereignissen (D0007).

Same rules as the hard gates in ``availability``: a warning on a requested line
is exactly what would block its confirmation. Lines that already occupy material
can still conflict when stock was lost or something came back late.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.damage import DAMAGE_KIND_DAMAGE, Damage
from lamathek.models.loan import (
    LINE_STATUS_DRAFT,
    LINE_STATUS_REQUESTED,
    LINE_STATUSES_BLOCKING,
    LOAN_PHASE_DRAFT,
    Loan,
    LoanLine,
)
from lamathek.services.availability import (
    Conflict,
    Interval,
    line_conflicts,
    line_interval,
    loan_interval,
)
from lamathek.services.piece_availability import (
    damage_is_open,
    piece_has_open_severe_damage,
    piece_has_open_total_loss,
)

_OPEN_STATUSES = (LINE_STATUS_DRAFT, LINE_STATUS_REQUESTED, *LINE_STATUSES_BLOCKING)


def _line_label(line: LoanLine) -> str:
    if line.piece is not None:
        return line.piece.name
    if line.material_type is not None:
        from lamathek.services.variants import line_stock_name

        return f"{line.quantity or 0} × {line_stock_name(line)}"
    return ""


def _period_for(loan: Loan, line: LoanLine) -> Interval | None:
    """Drafts are judged by the wished period; everything else by the agreed one."""
    if line.status in LINE_STATUSES_BLOCKING:
        return line_interval(loan, line)
    if loan.phase == LOAN_PHASE_DRAFT:
        return loan_interval(loan, wish=True) or loan_interval(loan)
    return loan_interval(loan)


def _requested_elsewhere(
    session: Session, loan: Loan, line: LoanLine, interval: Interval
) -> list[Conflict]:
    """Other open requests for the same piece in the same period (information only)."""
    if line.piece_id is None:
        return []
    stmt = (
        select(LoanLine, Loan)
        .join(Loan, LoanLine.loan_id == Loan.id)
        .where(
            LoanLine.piece_id == line.piece_id,
            LoanLine.status == LINE_STATUS_REQUESTED,
            Loan.id != loan.id,
        )
        .options(selectinload(Loan.group), selectinload(Loan.event))
    )
    found = []
    for _other_line, other_loan in session.execute(stmt).all():
        other = loan_interval(other_loan)
        if other is not None and other.overlaps(interval):
            found.append(
                Conflict(
                    "piece_requested_elsewhere",
                    line_id=line.id,
                    piece_id=line.piece_id,
                    other_loan=other_loan,
                )
            )
    return found


def _mild_damage(session: Session, line: LoanLine) -> list[Conflict]:
    if line.piece_id is None:
        return []
    damages = session.scalars(
        select(Damage)
        .where(
            Damage.piece_id == line.piece_id,
            Damage.kind == DAMAGE_KIND_DAMAGE,
            Damage.severe.is_(False),
        )
        .options(selectinload(Damage.repair))
    ).all()
    if any(damage_is_open(d) for d in damages):
        return [Conflict("piece_mild_damage", line_id=line.id, piece_id=line.piece_id)]
    return []


def line_warnings(session: Session, loan: Loan, line: LoanLine) -> list[dict[str, Any]]:
    if line.status not in _OPEN_STATUSES:
        return []
    interval = _period_for(loan, line)
    conflicts: list[Conflict] = []
    if interval is not None:
        conflicts.extend(
            c for c in line_conflicts(session, loan, line, interval=interval)
            if c.code != "pickup_required"
        )
        conflicts.extend(_requested_elsewhere(session, loan, line, interval))
    elif line.piece_id is not None:
        # Without dates only the piece's state can be judged.
        from lamathek.services.availability import piece_state_conflicts

        conflicts.extend(piece_state_conflicts(session, line.piece))
        for conflict in conflicts:
            conflict.line_id = line.id
    conflicts.extend(_mild_damage(session, line))
    label = _line_label(line)
    for conflict in conflicts:
        conflict.line_id = line.id
    return [c.to_json(item_label=label) for c in conflicts]


def enrich_loan_detail_warnings(
    session: Session, loan: Loan
) -> tuple[list[dict], dict[int, list[dict]]]:
    """All warnings of the loan (each names its line), and the same grouped per line."""
    per_line: dict[int, list[dict]] = {}
    for line in loan.lines:
        found = line_warnings(session, loan, line)
        if found:
            per_line[line.id] = found
    flat = [warning for warnings in per_line.values() for warning in warnings]
    return flat, per_line


def piece_planned_loan_warnings(session: Session, piece_id: int) -> list[dict[str, Any]]:
    """On a lost or severely damaged piece: every Verleih that still counts on it."""
    if piece_has_open_total_loss(session, piece_id):
        code = "planned_loan_total_loss"
    elif piece_has_open_severe_damage(session, piece_id):
        code = "planned_loan_severe_damage"
    else:
        return []
    stmt = (
        select(LoanLine, Loan)
        .join(Loan, LoanLine.loan_id == Loan.id)
        .where(
            LoanLine.piece_id == piece_id,
            LoanLine.status.in_((LINE_STATUS_REQUESTED, *LINE_STATUSES_BLOCKING)),
        )
        .options(selectinload(Loan.group), selectinload(Loan.event))
    )
    return [
        Conflict(code, line_id=line.id, piece_id=piece_id, other_loan=loan).to_json()
        for line, loan in session.execute(stmt).all()
    ]
