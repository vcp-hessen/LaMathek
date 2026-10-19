"""Warnungen zu zeitlicher Belegung und Stück-Ereignissen (keine harten Sperren außer Bestätigung)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lamathek.models.loan import (
    LINE_STATUSES_BLOCKING,
    LOAN_KIND_PERMANENT,
    LOAN_PHASE_DRAFT,
    Loan,
    LoanLine,
)
from lamathek.services.material import total_stock_quantity
from lamathek.services.piece_availability import (
    damage_is_open,
    piece_has_open_severe_damage,
    piece_has_open_total_loss,
)
from lamathek.models.damage import DAMAGE_KIND_DAMAGE, DAMAGE_KIND_TOTAL_LOSS


def _loan_interval(loan: Loan) -> tuple[date | None, date | None]:
    start = loan.pickup_on
    end = loan.return_on if loan.kind != LOAN_KIND_PERMANENT else None
    return start, end


def _wish_interval(loan: Loan) -> tuple[date | None, date | None]:
    return loan.wish_pickup_on, loan.wish_return_on


def _intervals_overlap(
    a_start: date | None,
    a_end: date | None,
    b_start: date | None,
    b_end: date | None,
) -> bool:
    if a_start is None or b_start is None:
        return False
    a_end_eff = a_end or date.max
    b_end_eff = b_end or date.max
    return a_start <= b_end_eff and b_start <= a_end_eff


def _blocking_lines_on_other_loans(
    session: Session,
    *,
    inventory_id: int,
    exclude_loan_id: int,
    piece_id: int | None = None,
    material_type_id: int | None = None,
) -> list[tuple[Loan, LoanLine]]:
    stmt = select(LoanLine, Loan).join(Loan, LoanLine.loan_id == Loan.id).where(
        Loan.inventory_id == inventory_id,
        Loan.id != exclude_loan_id,
        Loan.phase != LOAN_PHASE_DRAFT,
        LoanLine.status.in_(LINE_STATUSES_BLOCKING),
    )
    if piece_id is not None:
        stmt = stmt.where(LoanLine.piece_id == piece_id)
    if material_type_id is not None:
        stmt = stmt.where(LoanLine.material_type_id == material_type_id)
    return [(loan, line) for line, loan in session.execute(stmt).all()]


def _warn(code: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, **extra}


def _blocking_stock_qty_on_loan(
    session: Session, loan_id: int, material_type_id: int
) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(LoanLine.quantity), 0)).where(
            LoanLine.loan_id == loan_id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.status.in_(LINE_STATUSES_BLOCKING),
        )
    )
    return int(total or 0)


def loan_schedule_warnings(session: Session, loan: Loan) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    start, end = _loan_interval(loan)
    if start is None:
        return warnings
    seen: set[str] = set()
    for line in loan.lines:
        if line.status not in LINE_STATUSES_BLOCKING:
            continue
        if line.piece_id is not None:
            for other_loan, other_line in _blocking_lines_on_other_loans(
                session,
                inventory_id=loan.inventory_id,
                exclude_loan_id=loan.id,
                piece_id=line.piece_id,
            ):
                o_start, o_end = _loan_interval(other_loan)
                if not _intervals_overlap(start, end, o_start, o_end):
                    continue
                key = f"piece_overlap:{line.piece_id}:{other_loan.id}"
                if key in seen:
                    continue
                seen.add(key)
                warnings.append(
                    _warn(
                        "piece_date_overlap",
                        pieceId=line.piece_id,
                        otherLoanId=other_loan.id,
                        lineId=line.id,
                    )
                )
        elif line.material_type_id is not None and line.quantity:
            mt_id = line.material_type_id
            needed = 0
            for ln in loan.lines:
                if (
                    ln.material_type_id == mt_id
                    and ln.status in LINE_STATUSES_BLOCKING
                    and ln.quantity
                ):
                    needed += ln.quantity
            for other_loan, _ in _blocking_lines_on_other_loans(
                session,
                inventory_id=loan.inventory_id,
                exclude_loan_id=loan.id,
                material_type_id=mt_id,
            ):
                o_start, o_end = _loan_interval(other_loan)
                if not _intervals_overlap(start, end, o_start, o_end):
                    continue
                other_qty = _blocking_stock_qty_on_loan(session, other_loan.id, mt_id)
                if other_qty + needed > total_stock_quantity(session, mt_id):
                    key = f"stock_overlap:{mt_id}:{other_loan.id}"
                    if key in seen:
                        continue
                    seen.add(key)
                    warnings.append(
                        _warn(
                            "stock_date_overlap",
                            materialTypeId=mt_id,
                            otherLoanId=other_loan.id,
                        )
                    )
    return warnings


def borrower_wish_warnings(session: Session, loan: Loan) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    w_start, w_end = _wish_interval(loan)
    if w_start is None:
        return warnings
    for line in loan.lines:
        if line.piece_id is None:
            continue
        for other_loan, _ in _blocking_lines_on_other_loans(
            session,
            inventory_id=loan.inventory_id,
            exclude_loan_id=loan.id,
            piece_id=line.piece_id,
        ):
            o_start, o_end = _loan_interval(other_loan)
            if not _intervals_overlap(w_start, w_end, o_start, o_end):
                continue
            warnings.append(
                _warn(
                    "piece_wish_overlap",
                    pieceId=line.piece_id,
                    otherLoanId=other_loan.id,
                    lineId=line.id,
                )
            )
    return warnings


def line_piece_event_warnings(session: Session, line: LoanLine) -> list[dict[str, Any]]:
    if line.piece_id is None:
        return []
    piece_id = line.piece_id
    warnings: list[dict[str, Any]] = []
    if piece_has_open_total_loss(session, piece_id):
        warnings.append(_warn("piece_total_loss", pieceId=piece_id, lineId=line.id))
    elif piece_has_open_severe_damage(session, piece_id):
        warnings.append(_warn("piece_severe_damage", pieceId=piece_id, lineId=line.id))
    from sqlalchemy.orm import selectinload
    from lamathek.models.damage import Damage

    for damage in session.scalars(
        select(Damage)
        .where(Damage.piece_id == piece_id, Damage.kind == DAMAGE_KIND_DAMAGE)
        .options(selectinload(Damage.repair))
    ).all():
        if damage.severe or damage.kind == DAMAGE_KIND_TOTAL_LOSS:
            continue
        if damage_is_open(damage):
            warnings.append(_warn("piece_mild_damage", pieceId=piece_id, lineId=line.id))
            break
    return warnings


def piece_planned_loan_warnings(session: Session, piece_id: int) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    stmt = select(LoanLine, Loan).join(Loan, LoanLine.loan_id == Loan.id).where(
        LoanLine.piece_id == piece_id,
        LoanLine.status.in_(LINE_STATUSES_BLOCKING),
    )
    for line, loan in session.execute(stmt).all():
        if piece_has_open_total_loss(session, piece_id):
            warnings.append(
                _warn(
                    "planned_loan_total_loss",
                    loanId=loan.id,
                    lineId=line.id,
                )
            )
        elif piece_has_open_severe_damage(session, piece_id):
            warnings.append(
                _warn(
                    "planned_loan_severe_damage",
                    loanId=loan.id,
                    lineId=line.id,
                )
            )
    return warnings


def enrich_loan_detail_warnings(session: Session, loan: Loan) -> tuple[list[dict], dict[int, list[dict]]]:
    loan_warnings = loan_schedule_warnings(session, loan)
    if loan.phase == LOAN_PHASE_DRAFT:
        loan_warnings = loan_warnings + borrower_wish_warnings(session, loan)
    line_warnings: dict[int, list[dict]] = {}
    for line in loan.lines:
        lw = line_piece_event_warnings(session, line)
        if lw:
            line_warnings[line.id] = lw
    return loan_warnings, line_warnings
