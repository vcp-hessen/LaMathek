"""Einzelteil-Verfügbarkeit über Stück-Ereignisse (Schaden / Totalverlust)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.damage import (
    DAMAGE_KIND_DAMAGE,
    DAMAGE_KIND_TOTAL_LOSS,
    RESOLUTION_CANCELLED_MISTAKE,
    RESOLUTION_FOUND_AGAIN,
    Damage,
    Repair,
)
from lamathek.models.loan import LoanLine


def _open_damages(session: Session, piece_id: int) -> list[Damage]:
    return list(
        session.scalars(
            select(Damage)
            .where(Damage.piece_id == piece_id)
            .options(selectinload(Damage.repair))
            .order_by(Damage.id.desc())
        ).all()
    )


def damage_is_open(damage: Damage) -> bool:
    return damage.repair is None


def _open_event_query(kind: str):
    """Damages of ``kind`` without a Repair (i.e. still open)."""
    return (
        select(Damage.piece_id)
        .outerjoin(Repair, Repair.damage_id == Damage.id)
        .where(Damage.kind == kind, Repair.id.is_(None))
    )


def piece_has_open_total_loss(session: Session, piece_id: int) -> bool:
    query = _open_event_query(DAMAGE_KIND_TOTAL_LOSS).where(Damage.piece_id == piece_id)
    return session.scalar(query.limit(1)) is not None


def piece_has_open_severe_damage(session: Session, piece_id: int) -> bool:
    query = _open_event_query(DAMAGE_KIND_DAMAGE).where(
        Damage.piece_id == piece_id, Damage.severe.is_(True)
    )
    return session.scalar(query.limit(1)) is not None


def piece_is_blocked_for_lending(session: Session, piece_id: int) -> bool:
    return piece_has_open_total_loss(session, piece_id) or piece_has_open_severe_damage(
        session, piece_id
    )


def open_total_loss_for_line(session: Session, loan_line_id: int) -> Damage | None:
    damage = session.scalar(
        select(Damage)
        .where(
            Damage.loan_line_id == loan_line_id,
            Damage.kind == DAMAGE_KIND_TOTAL_LOSS,
        )
        .options(selectinload(Damage.repair))
        .order_by(Damage.id.desc())
        .limit(1)
    )
    if damage is None or not damage_is_open(damage):
        return None
    return damage


def open_total_loss_for_piece(session: Session, piece_id: int) -> Damage | None:
    for damage in _open_damages(session, piece_id):
        if damage.kind == DAMAGE_KIND_TOTAL_LOSS and damage_is_open(damage):
            return damage
    return None


def create_total_loss_for_line(
    session: Session,
    line: LoanLine,
    *,
    recorded_on: date,
    note: str | None = None,
) -> Damage | None:
    if line.piece_id is None:
        return None
    existing = open_total_loss_for_line(session, line.id)
    if existing is not None:
        return existing
    damage = Damage(
        piece_id=line.piece_id,
        recorded_on=recorded_on,
        note=note,
        severe=True,
        kind=DAMAGE_KIND_TOTAL_LOSS,
        loan_id=line.loan_id,
        loan_line_id=line.id,
    )
    session.add(damage)
    session.flush()
    return damage


def _resolve_damage(
    session: Session,
    damage: Damage,
    *,
    recorded_on: date,
    resolution_kind: str,
    note: str | None,
) -> Repair:
    if damage.repair is not None:
        raise ValueError("already_repaired")
    repair = Repair(
        damage_id=damage.id,
        recorded_on=recorded_on,
        note=note,
        resolution_kind=resolution_kind,
    )
    session.add(repair)
    session.flush()
    return repair


def cancel_total_loss_for_line(
    session: Session,
    loan_line_id: int,
    *,
    recorded_on: date,
    note: str | None = None,
) -> None:
    damage = open_total_loss_for_line(session, loan_line_id)
    if damage is None:
        return
    _resolve_damage(
        session,
        damage,
        recorded_on=recorded_on,
        resolution_kind=RESOLUTION_CANCELLED_MISTAKE,
        note=note,
    )


def record_found_again_for_piece(
    session: Session,
    piece_id: int,
    *,
    recorded_on: date,
    reason: str,
) -> Repair:
    damage = open_total_loss_for_piece(session, piece_id)
    if damage is None:
        raise ValueError("no_open_total_loss")
    return _resolve_damage(
        session,
        damage,
        recorded_on=recorded_on,
        resolution_kind=RESOLUTION_FOUND_AGAIN,
        note=reason.strip(),
    )


def write_off_piece(
    session: Session, piece_id: int, *, recorded_on: date, reason: str
) -> Repair:
    """The total loss is final: close it and retire the piece (D0009)."""
    from lamathek.models.damage import RESOLUTION_WRITTEN_OFF
    from lamathek.models.material import ITEM_STATUS_RETIRED, Piece

    damage = open_total_loss_for_piece(session, piece_id)
    if damage is None:
        raise ValueError("no_open_total_loss")
    repair = _resolve_damage(
        session,
        damage,
        recorded_on=recorded_on,
        resolution_kind=RESOLUTION_WRITTEN_OFF,
        note=reason.strip(),
    )
    session.get(Piece, piece_id).status = ITEM_STATUS_RETIRED
    return repair


def piece_found_again_eligible(session: Session, piece_id: int) -> bool:
    if not piece_has_open_total_loss(session, piece_id):
        return False
    from lamathek.models.loan import LOAN_PHASE_CLOSED, Loan, LoanLine
    from lamathek.models.loan import LINE_STATUS_NOT_RETURNED

    open_not_returned = session.scalar(
        select(LoanLine.id)
        .join(Loan, LoanLine.loan_id == Loan.id)
        .where(
            LoanLine.piece_id == piece_id,
            LoanLine.status == LINE_STATUS_NOT_RETURNED,
            Loan.phase != LOAN_PHASE_CLOSED,
        )
        .limit(1)
    )
    return open_not_returned is None


def piece_ids_with_open_total_loss(session: Session, piece_ids: list[int]) -> set[int]:
    if not piece_ids:
        return set()
    query = _open_event_query(DAMAGE_KIND_TOTAL_LOSS).where(Damage.piece_id.in_(piece_ids))
    return set(session.scalars(query).all())
