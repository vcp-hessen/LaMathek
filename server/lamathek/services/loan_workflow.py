from datetime import date

from sqlalchemy.orm import Session

from lamathek.models.loan import (
    LINE_STATUS_CONFIRMED,
    LINE_STATUS_DRAFT,
    LINE_STATUS_NOT_PACKED,
    LINE_STATUS_NOT_PICKED_UP,
    LINE_STATUS_NOT_RETURNED,
    LINE_STATUS_PACKED,
    LINE_STATUS_PICKED_UP,
    LINE_STATUS_REQUESTED,
    LINE_STATUS_RESTOCKED,
    LINE_STATUS_RETURN_REPORTED,
    LINE_STATUS_UNAVAILABLE,
    LINE_STATUS_WITHDRAWN,
    LINE_STATUSES_TERMINAL,
    LOAN_KIND_PERMANENT,
    LOAN_KIND_SHORT,
    LOAN_PHASE_ACTIVE,
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_DRAFT,
    Loan,
    LoanLine,
)
from lamathek.models.material import MaterialType
from lamathek.models.user import User
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.loan_access import user_is_borrower
from lamathek.services.loans import (
    _validate_piece_available,
    _validate_stock_available,
    loan_by_id,
)
from lamathek.services.loan_notifications import notify_loan_action


def line_is_terminal(line: LoanLine, *, consumable: bool = False) -> bool:
    if line.status in LINE_STATUSES_TERMINAL:
        return True
    return False


def _material_type_consumable(session: Session, line: LoanLine) -> bool:
    if line.material_type_id is None:
        return False
    mt = session.get(MaterialType, line.material_type_id)
    return bool(mt and mt.consumable)


def refresh_loan_phase(session: Session, loan: Loan) -> None:
    if loan.phase == LOAN_PHASE_DRAFT:
        return
    if not loan.lines:
        return
    for line in loan.lines:
        consumable = _material_type_consumable(session, line)
        if not line_is_terminal(line, consumable=consumable):
            if loan.phase == LOAN_PHASE_CLOSED:
                loan.phase = LOAN_PHASE_ACTIVE
            return
    loan.phase = LOAN_PHASE_CLOSED


def _borrower_phone_required(user: User) -> None:
    if not (user.phone or "").strip():
        raise ValueError("borrower_phone_required")


def _validate_dates(
    *,
    kind: str,
    pickup_on: date | None,
    return_on: date | None,
) -> None:
    if pickup_on is None:
        raise ValueError("pickup_required")
    if kind == LOAN_KIND_PERMANENT:
        if return_on is not None:
            raise ValueError("invalid_permanent_fields")
        return
    if return_on is None:
        raise ValueError("return_required")
    if return_on < pickup_on:
        raise ValueError("invalid_date_range")


def _lines_for_loan(session: Session, loan: Loan, line_ids: list[int]) -> list[LoanLine]:
    by_id = {line.id: line for line in loan.lines}
    result: list[LoanLine] = []
    for lid in line_ids:
        line = by_id.get(lid)
        if line is None:
            raise ValueError("invalid_line")
        result.append(line)
    return result


def _actor_is_borrower_or_manager(session: Session, actor: User, loan: Loan) -> bool:
    if user_is_borrower(actor, loan):
        return True
    return user_can_manage_inventory(session, actor, loan.inventory)


def submit_loan_request(
    session: Session,
    loan: Loan,
    *,
    pickup_on: date,
    return_on: date | None,
    actor: User,
) -> Loan:
    if not user_is_borrower(actor, loan):
        raise ValueError("forbidden")
    if loan.phase != LOAN_PHASE_DRAFT:
        raise ValueError("loan_not_editable")
    if not loan.lines:
        raise ValueError("empty_loan")
    borrower = loan.borrower_user
    _borrower_phone_required(borrower)
    _validate_dates(kind=loan.kind, pickup_on=pickup_on, return_on=return_on)
    loan.wish_pickup_on = pickup_on
    loan.wish_return_on = return_on if loan.kind != LOAN_KIND_PERMANENT else None
    loan.pickup_on = pickup_on
    loan.return_on = return_on if loan.kind != LOAN_KIND_PERMANENT else None
    notified_ids: list[int] = []
    for line in loan.lines:
        if line.status == LINE_STATUS_DRAFT:
            line.status = LINE_STATUS_REQUESTED
            line.request_notified = True
            notified_ids.append(line.id)
    loan.phase = LOAN_PHASE_ACTIVE
    session.commit()
    notify_loan_action(session, loan, "request", actor=actor, line_ids=notified_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def confirm_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    if loan.contact_user_id is None:
        raise ValueError("invalid_contact")
    contact = session.get(User, loan.contact_user_id)
    if contact is None or not user_can_manage_inventory(session, contact, loan.inventory):
        raise ValueError("invalid_contact")
    if loan.pickup_on is None:
        raise ValueError("pickup_required")
    if loan.kind != LOAN_KIND_PERMANENT and loan.return_on is None:
        raise ValueError("return_required")
    _validate_dates(
        kind=loan.kind,
        pickup_on=loan.pickup_on,
        return_on=loan.return_on,
    )
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status != LINE_STATUS_REQUESTED:
            raise ValueError("invalid_line_status")
        if line.piece_id is not None:
            _validate_piece_available(session, line.piece_id, exclude_loan_id=loan.id)
        elif line.material_type_id is not None and line.quantity is not None:
            _validate_stock_available(
                session,
                loan.inventory_id,
                line.material_type_id,
                line.quantity,
                exclude_loan_id=loan.id,
                from_set_origin=line.origin_set_id is not None,
            )
        line.status = LINE_STATUS_CONFIRMED
    if loan.phase == LOAN_PHASE_DRAFT:
        loan.phase = LOAN_PHASE_ACTIVE
    session.commit()
    notify_loan_action(session, loan, "confirm", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def decline_lines(
    session: Session,
    loan: Loan,
    entries: list[dict],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    line_ids: list[int] = []
    for entry in entries:
        line_id = entry.get("lineId")
        reason = entry.get("reason")
        if not isinstance(line_id, int) or not isinstance(reason, str) or not reason.strip():
            raise ValueError("invalid_decline")
        line = session.get(LoanLine, line_id)
        if line is None or line.loan_id != loan.id:
            raise ValueError("invalid_line")
        if line.status not in (LINE_STATUS_REQUESTED, LINE_STATUS_CONFIRMED):
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_UNAVAILABLE
        line.reason = reason.strip()
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
    notify_loan_action(session, loan, "decline", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def replace_line(
    session: Session,
    loan: Loan,
    *,
    original_line_id: int,
    reason: str,
    replacement: dict,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    original = session.get(LoanLine, original_line_id)
    if original is None or original.loan_id != loan.id:
        raise ValueError("invalid_line")
    if original.status not in (LINE_STATUS_REQUESTED, LINE_STATUS_CONFIRMED):
        raise ValueError("invalid_line_status")
    if not reason.strip():
        raise ValueError("reason_required")
    original.status = LINE_STATUS_UNAVAILABLE
    original.reason = reason.strip()

    new_line = LoanLine(
        loan_id=loan.id,
        status=LINE_STATUS_CONFIRMED,
        replaces_line_id=original.id,
        origin_set_id=original.origin_set_id,
        origin_set_name=original.origin_set_name,
        origin_set_role=original.origin_set_role,
    )
    if "pieceId" in replacement:
        piece_id = replacement["pieceId"]
        _validate_piece_available(session, piece_id, exclude_loan_id=loan.id)
        new_line.piece_id = piece_id
    elif "materialTypeId" in replacement and "quantity" in replacement:
        new_line.material_type_id = replacement["materialTypeId"]
        new_line.quantity = replacement["quantity"]
        _validate_stock_available(
            session,
            loan.inventory_id,
            new_line.material_type_id,
            new_line.quantity,
            exclude_loan_id=loan.id,
            from_set_origin=new_line.origin_set_id is not None,
        )
    else:
        raise ValueError("invalid_replacement")
    session.add(new_line)
    session.commit()
    notify_loan_action(
        session,
        loan,
        "replace",
        actor=actor,
        line_ids=[original.id, new_line.id],
    )
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def withdraw_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not user_is_borrower(actor, loan) and not user_can_manage_inventory(
        session, actor, loan.inventory
    ):
        raise ValueError("forbidden")
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status not in (LINE_STATUS_REQUESTED, LINE_STATUS_CONFIRMED):
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_WITHDRAWN
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
    notify_loan_action(session, loan, "withdraw", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def pack_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status != LINE_STATUS_CONFIRMED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_PACKED
    session.commit()
    notify_loan_action(session, loan, "pack", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def unpack_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status != LINE_STATUS_PACKED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_CONFIRMED
    session.commit()
    notify_loan_action(session, loan, "unpack", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def mark_not_packed(
    session: Session,
    loan: Loan,
    entries: list[dict],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    line_ids: list[int] = []
    for entry in entries:
        line_id = entry.get("lineId")
        reason = entry.get("reason")
        if not isinstance(line_id, int) or not isinstance(reason, str) or not reason.strip():
            raise ValueError("invalid_entry")
        line = session.get(LoanLine, line_id)
        if line is None or line.loan_id != loan.id or line.status != LINE_STATUS_PACKED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_NOT_PACKED
        line.reason = reason.strip()
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
    notify_loan_action(session, loan, "not_packed", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def pickup_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status != LINE_STATUS_PACKED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_PICKED_UP
    session.commit()
    notify_loan_action(session, loan, "pickup", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def undo_pickup_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status != LINE_STATUS_PICKED_UP:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_PACKED
    session.commit()
    notify_loan_action(session, loan, "undo_pickup", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def mark_not_picked_up(
    session: Session,
    loan: Loan,
    entries: list[dict],
    *,
    actor: User,
) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    line_ids: list[int] = []
    for entry in entries:
        line_id = entry.get("lineId")
        reason = entry.get("reason")
        if not isinstance(line_id, int) or not isinstance(reason, str) or not reason.strip():
            raise ValueError("invalid_entry")
        line = session.get(LoanLine, line_id)
        if line is None or line.loan_id != loan.id or line.status != LINE_STATUS_PACKED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_NOT_PICKED_UP
        line.reason = reason.strip()
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
    notify_loan_action(session, loan, "not_picked_up", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def report_return_lines(
    session: Session,
    loan: Loan,
    line_ids: list[int],
    *,
    actor: User,
) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        if line.status != LINE_STATUS_PICKED_UP:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_RETURN_REPORTED
    session.commit()
    notify_loan_action(session, loan, "report_return", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def _copy_line_origin(source: LoanLine, target: LoanLine) -> None:
    target.origin_set_id = source.origin_set_id
    target.origin_set_name = source.origin_set_name
    target.origin_set_role = source.origin_set_role


def _reason_from_entry(entry: dict) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason_required")
    return reason.strip()


def restock_lines(
    session: Session,
    loan: Loan,
    entries: list[dict],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    from lamathek.services.material import apply_stock_loss

    line_ids: list[int] = []
    for entry in entries:
        line_id = entry.get("lineId")
        if not isinstance(line_id, int):
            raise ValueError("invalid_entry")
        line = session.get(LoanLine, line_id)
        if line is None or line.loan_id != loan.id:
            raise ValueError("invalid_line")
        if line.status != LINE_STATUS_RETURN_REPORTED:
            raise ValueError("invalid_line_status")
        if line.piece_id is not None:
            line.status = LINE_STATUS_RESTOCKED
            line_ids.append(line_id)
            continue
        if line.material_type_id is None or line.quantity is None:
            raise ValueError("invalid_line")
        consumable = _material_type_consumable(session, line)
        returned = entry.get("returnedQuantity")
        if returned is None:
            returned = line.quantity
        if not isinstance(returned, int) or returned < 0 or returned > line.quantity:
            raise ValueError("invalid_entry")
        if consumable:
            if returned == 0:
                reason = _reason_from_entry(entry)
                apply_stock_loss(session, line.material_type_id, line.quantity)
                line.status = LINE_STATUS_NOT_RETURNED
                line.reason = reason
                line.returned_quantity = 0
            else:
                consumed = line.quantity - returned
                if consumed > 0:
                    apply_stock_loss(session, line.material_type_id, consumed)
                line.returned_quantity = returned
                line.status = LINE_STATUS_RESTOCKED
            line_ids.append(line_id)
            continue
        if returned == line.quantity:
            line.returned_quantity = returned
            line.status = LINE_STATUS_RESTOCKED
            line_ids.append(line_id)
            continue
        if returned == 0:
            reason = _reason_from_entry(entry)
            apply_stock_loss(session, line.material_type_id, line.quantity)
            line.status = LINE_STATUS_NOT_RETURNED
            line.reason = reason
            line.returned_quantity = 0
            line_ids.append(line_id)
            continue
        reason = _reason_from_entry(entry)
        missing = line.quantity - returned
        line.quantity = returned
        line.returned_quantity = returned
        line.status = LINE_STATUS_RESTOCKED
        lost_line = LoanLine(
            loan_id=loan.id,
            material_type_id=line.material_type_id,
            quantity=missing,
            status=LINE_STATUS_NOT_RETURNED,
            reason=reason,
            split_from_line_id=line.id,
        )
        _copy_line_origin(line, lost_line)
        apply_stock_loss(session, line.material_type_id, missing)
        session.add(lost_line)
        session.flush()
        line_ids.append(line_id)
        line_ids.append(lost_line.id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
    notify_loan_action(session, loan, "restock", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def record_loss_lines(
    session: Session,
    loan: Loan,
    entries: list[dict],
    *,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    from lamathek.services.material import apply_stock_loss

    line_ids: list[int] = []
    for entry in entries:
        line_id = entry.get("lineId")
        quantity = entry.get("quantity")
        if not isinstance(line_id, int):
            raise ValueError("invalid_entry")
        line = session.get(LoanLine, line_id)
        if line is None or line.loan_id != loan.id:
            raise ValueError("invalid_line")
        if line.status not in (
            LINE_STATUS_PICKED_UP,
            LINE_STATUS_RETURN_REPORTED,
        ):
            raise ValueError("invalid_line_status")
        reason = _reason_from_entry(entry)
        if line.material_type_id is not None and line.quantity is not None:
            qty = quantity if isinstance(quantity, int) else line.quantity
            apply_stock_loss(session, line.material_type_id, qty)
        line.status = LINE_STATUS_NOT_RETURNED
        line.reason = reason
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
    notify_loan_action(session, loan, "loss", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


_PRE_CONFIRM_LINE_STATUSES = frozenset(
    {LINE_STATUS_DRAFT, LINE_STATUS_REQUESTED}
)

_CANCEL_FORBIDDEN_LINE_STATUSES = frozenset(
    {
        LINE_STATUS_PACKED,
        LINE_STATUS_PICKED_UP,
        LINE_STATUS_RETURN_REPORTED,
    }
)

_CANCEL_WITHDRAW_LINE_STATUSES = frozenset(
    {
        LINE_STATUS_DRAFT,
        LINE_STATUS_REQUESTED,
        LINE_STATUS_CONFIRMED,
    }
)

_SKIP_PICKUP_BLOCK_EARLY = frozenset(
    {
        LINE_STATUS_DRAFT,
        LINE_STATUS_REQUESTED,
        LINE_STATUS_CONFIRMED,
    }
)

_SKIP_PICKUP_BLOCK_LATE = frozenset(
    {
        LINE_STATUS_PICKED_UP,
        LINE_STATUS_RETURN_REPORTED,
    }
)


def _require_borrower(actor: User, loan: Loan) -> None:
    if not user_is_borrower(actor, loan):
        raise ValueError("forbidden")


def hand_draft_to_borrower(
    session: Session,
    loan: Loan,
    *,
    borrower_user_id: int,
    actor: User,
) -> Loan:
    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")
    if loan.phase != LOAN_PHASE_DRAFT:
        raise ValueError("invalid_loan_state")
    if borrower_user_id == loan.borrower_user_id:
        return loan_by_id(session, loan.id)  # type: ignore[return-value]
    borrower = session.get(User, borrower_user_id)
    if borrower is None:
        raise ValueError("invalid_borrower")
    loan.borrower_user_id = borrower_user_id
    loan.contact_user_id = actor.id
    loan.phase = LOAN_PHASE_ACTIVE
    line_ids: list[int] = []
    for line in loan.lines:
        if line.status == LINE_STATUS_DRAFT:
            line.status = LINE_STATUS_REQUESTED
            line.request_notified = True
            line_ids.append(line.id)
    session.commit()
    if line_ids:
        notify_loan_action(session, loan, "request", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def notify_added_lines(session: Session, loan: Loan, *, actor: User) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    if loan.phase == LOAN_PHASE_DRAFT:
        raise ValueError("invalid_loan_state")
    line_ids = [
        line.id
        for line in loan.lines
        if line.status == LINE_STATUS_REQUESTED and not line.request_notified
    ]
    if not line_ids:
        raise ValueError("empty_notify")
    for line in loan.lines:
        if line.id in line_ids:
            line.request_notified = True
    session.commit()
    notify_loan_action(session, loan, "request", actor=actor, line_ids=line_ids)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def delete_unreleased_loan(session: Session, loan: Loan, *, actor: User) -> None:
    _require_borrower(actor, loan)
    if loan.phase != LOAN_PHASE_DRAFT:
        raise ValueError("invalid_loan_state")
    session.delete(loan)
    session.commit()


def cancel_unpacked_loan(session: Session, loan: Loan, *, actor: User) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    if loan.phase != LOAN_PHASE_ACTIVE:
        raise ValueError("invalid_loan_state")
    if any(line.status in _CANCEL_FORBIDDEN_LINE_STATUSES for line in loan.lines):
        raise ValueError("invalid_loan_state")
    withdrawn_ids: list[int] = []
    for line in loan.lines:
        if line.status in _CANCEL_WITHDRAW_LINE_STATUSES:
            line.status = LINE_STATUS_WITHDRAWN
            withdrawn_ids.append(line.id)
    if not loan.lines:
        loan.phase = LOAN_PHASE_CLOSED
    session.commit()
    refresh_loan_phase(session, loan)
    if not loan.lines and loan.phase != LOAN_PHASE_CLOSED:
        loan.phase = LOAN_PHASE_CLOSED
    session.commit()
    if withdrawn_ids:
        notify_loan_action(
            session, loan, "cancel", actor=actor, line_ids=withdrawn_ids
        )
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def skip_pickup_to_return(session: Session, loan: Loan, *, actor: User) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    if not any(line.status == LINE_STATUS_PACKED for line in loan.lines):
        raise ValueError("invalid_loan_state")
    if any(line.status in _SKIP_PICKUP_BLOCK_EARLY for line in loan.lines):
        raise ValueError("invalid_loan_state")
    if any(line.status in _SKIP_PICKUP_BLOCK_LATE for line in loan.lines):
        raise ValueError("invalid_loan_state")
    line_ids: list[int] = []
    for line in loan.lines:
        if line.status == LINE_STATUS_PACKED:
            line.status = LINE_STATUS_RETURN_REPORTED
            line_ids.append(line.id)
    session.commit()
    notify_loan_action(
        session, loan, "skip_pickup", actor=actor, line_ids=line_ids
    )
    return loan_by_id(session, loan.id)  # type: ignore[return-value]

