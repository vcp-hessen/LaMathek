"""Verlust und Verbrauch bei Mengen als Ereignisse (D0009).

Mengenposten are never deleted or shrunk by a loss. A ``lost`` event keeps the
lot's Soll-Anzahl and only reduces what can be lent while it is open; resolving
it (found again, written off, booked by mistake) is a single update, so
corrections never have to rebuild a lot with its label, variant and photos.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.material import (
    ITEM_STATUS_ACTIVE,
    LOSS_RESOLUTION_CANCELLED_MISTAKE,
    LOSS_RESOLUTION_FOUND_AGAIN,
    LOSS_RESOLUTION_WRITTEN_OFF,
    STOCK_LOSS_CONSUMED,
    STOCK_LOSS_LOST,
    StockLoss,
    StockLot,
)
from lamathek.models.user import User
from lamathek.timezone import instance_today


def open_lost_by_lot(session: Session, lot_ids: list[int]) -> dict[int, int]:
    """Unresolved lost quantity per lot."""
    if not lot_ids:
        return {}
    rows = session.execute(
        select(StockLoss.stock_lot_id, func.sum(StockLoss.quantity))
        .where(
            StockLoss.stock_lot_id.in_(lot_ids),
            StockLoss.kind == STOCK_LOSS_LOST,
            StockLoss.resolution_kind.is_(None),
        )
        .group_by(StockLoss.stock_lot_id)
    ).all()
    return {lot_id: int(total or 0) for lot_id, total in rows}


def active_lots(
    session: Session, material_type_id: int, variant_key: str | None = None
) -> list[StockLot]:
    """Active lots of a Materialart, optionally only one variant combination (#12)."""
    from lamathek.services.variants import lot_variant_key

    lots = list(
        session.scalars(
            select(StockLot)
            .where(
                StockLot.material_type_id == material_type_id,
                StockLot.status == ITEM_STATUS_ACTIVE,
            )
            .options(
                selectinload(StockLot.variant_selections),
                selectinload(StockLot.material_type),
            )
            .order_by(StockLot.id)
        ).all()
    )
    if variant_key is None:
        return lots
    return [lot for lot in lots if lot_variant_key(lot) == variant_key]


def lot_available_quantity(lot: StockLot, open_lost: int) -> int:
    return max(0, lot.quantity - open_lost)


def available_stock_quantity(
    session: Session, material_type_id: int, variant_key: str | None = None
) -> int:
    """What can be lent at all: active lots minus open losses (of one combination if given)."""
    lots = active_lots(session, material_type_id, variant_key)
    lost = open_lost_by_lot(session, [lot.id for lot in lots])
    return sum(lot_available_quantity(lot, lost.get(lot.id, 0)) for lot in lots)


def available_by_variant(session: Session, material_type_id: int) -> dict[str, int]:
    """Lendable quantity per variant combination of a Materialart."""
    from lamathek.services.variants import lot_variant_key

    lots = active_lots(session, material_type_id)
    lost = open_lost_by_lot(session, [lot.id for lot in lots])
    result: dict[str, int] = {}
    for lot in lots:
        key = lot_variant_key(lot)
        result[key] = result.get(key, 0) + lot_available_quantity(lot, lost.get(lot.id, 0))
    return result


def _allocate(
    session: Session, material_type_id: int, quantity: int, variant_key: str | None
) -> list[tuple[StockLot, int]]:
    """Spread ``quantity`` over active lots of the combination that still have something."""
    lots = active_lots(session, material_type_id, variant_key)
    if not lots and variant_key is not None:
        # Nothing of that combination on record (any more): book on any lot of the type.
        lots = active_lots(session, material_type_id)
    lost = open_lost_by_lot(session, [lot.id for lot in lots])
    remaining = quantity
    parts: list[tuple[StockLot, int]] = []
    for lot in lots:
        take = min(lot_available_quantity(lot, lost.get(lot.id, 0)), remaining)
        if take > 0:
            parts.append((lot, take))
            remaining -= take
        if remaining == 0:
            break
    if remaining > 0:
        # More went missing than the records say exist: book the rest on the
        # first lot anyway so the loss is not lost; its availability floors at 0.
        if not lots:
            raise ValueError("invalid_loss")
        parts.append((lots[0], remaining))
    return parts


def book_stock_loss(
    session: Session,
    material_type_id: int,
    quantity: int,
    *,
    kind: str = STOCK_LOSS_LOST,
    loan_line_id: int | None = None,
    variant_key: str | None = None,
    reason: str = "",
    recorded_on: date | None = None,
) -> list[StockLoss]:
    """Record a loss (or consumption) of ``quantity``; consumption lowers the lots at once."""
    if quantity <= 0:
        raise ValueError("invalid_quantity")
    entries = []
    for lot, take in _allocate(session, material_type_id, quantity, variant_key):
        entry = StockLoss(
            stock_lot_id=lot.id,
            material_type_id=material_type_id,
            loan_line_id=loan_line_id,
            kind=kind,
            quantity=take,
            recorded_on=recorded_on or instance_today(),
            reason=reason.strip(),
        )
        if kind == STOCK_LOSS_CONSUMED:
            lot.quantity = max(0, lot.quantity - take)
        session.add(entry)
        entries.append(entry)
    session.flush()
    return entries


def _resolve(
    loss: StockLoss, resolution: str, *, actor: User | None, note: str, on: date | None
) -> None:
    loss.resolution_kind = resolution
    loss.resolved_on = on or instance_today()
    loss.resolution_note = note.strip()
    loss.resolved_by_user_id = actor.id if actor is not None else None


def cancel_line_losses(session: Session, loan_line_id: int, *, actor: User | None) -> None:
    """Correction of a wrongly booked loss or consumption on a Verleih line."""
    entries = session.scalars(
        select(StockLoss).where(
            StockLoss.loan_line_id == loan_line_id,
            (StockLoss.resolution_kind.is_(None))
            | (StockLoss.resolution_kind != LOSS_RESOLUTION_CANCELLED_MISTAKE),
        )
    ).all()
    for entry in entries:
        lowered_lot = entry.kind == STOCK_LOSS_CONSUMED or (
            entry.resolution_kind == LOSS_RESOLUTION_WRITTEN_OFF
        )
        if lowered_lot:
            entry.stock_lot.quantity += entry.quantity
        _resolve(entry, LOSS_RESOLUTION_CANCELLED_MISTAKE, actor=actor, note="", on=None)


def _open_loss(session: Session, loss_id: int, material_type_id: int | None = None) -> StockLoss:
    loss = session.get(StockLoss, loss_id)
    if loss is None or (material_type_id is not None and loss.material_type_id != material_type_id):
        raise ValueError("not_found")
    if not loss.is_open:
        raise ValueError("loss_not_open")
    return loss


def found_again(
    session: Session, loss_id: int, quantity: int, *, actor: User, reason: str
) -> StockLoss:
    """Part or all of an open loss is back; a partial find splits the event."""
    loss = _open_loss(session, loss_id)
    if not reason.strip():
        raise ValueError("reason_required")
    if quantity <= 0 or quantity > loss.quantity:
        raise ValueError("invalid_quantity")
    if quantity < loss.quantity:
        found = StockLoss(
            stock_lot_id=loss.stock_lot_id,
            material_type_id=loss.material_type_id,
            loan_line_id=loss.loan_line_id,
            kind=loss.kind,
            quantity=quantity,
            recorded_on=loss.recorded_on,
            reason=loss.reason,
        )
        loss.quantity -= quantity
        session.add(found)
        loss = found
    _resolve(loss, LOSS_RESOLUTION_FOUND_AGAIN, actor=actor, note=reason, on=None)
    session.flush()
    return loss


def write_off(session: Session, loss_id: int, *, actor: User, reason: str) -> StockLoss:
    """Final: the quantity will not come back, so the lot's Soll-Anzahl drops."""
    loss = _open_loss(session, loss_id)
    if not reason.strip():
        raise ValueError("reason_required")
    loss.stock_lot.quantity = max(0, loss.stock_lot.quantity - loss.quantity)
    _resolve(loss, LOSS_RESOLUTION_WRITTEN_OFF, actor=actor, note=reason, on=None)
    session.flush()
    return loss


def lot_has_losses(session: Session, lot_id: int) -> bool:
    return session.scalar(select(StockLoss.id).where(StockLoss.stock_lot_id == lot_id).limit(1)) is not None


def losses_for_material_type(session: Session, material_type_id: int) -> list[StockLoss]:
    return list(
        session.scalars(
            select(StockLoss)
            .where(StockLoss.material_type_id == material_type_id)
            .order_by(StockLoss.recorded_on.desc(), StockLoss.id.desc())
        ).all()
    )


def stock_loss_to_json(loss: StockLoss) -> dict:
    return {
        "id": loss.id,
        "stockLotId": loss.stock_lot_id,
        "materialTypeId": loss.material_type_id,
        "loanLineId": loss.loan_line_id,
        "loanId": loss.loan_line.loan_id if loss.loan_line is not None else None,
        "kind": loss.kind,
        "quantity": loss.quantity,
        "recordedOn": loss.recorded_on.isoformat(),
        "reason": loss.reason,
        "open": loss.is_open,
        "resolution": loss.resolution_kind,
        "resolvedOn": loss.resolved_on.isoformat() if loss.resolved_on else None,
        "resolutionNote": loss.resolution_note,
    }
