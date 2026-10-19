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
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_DRAFT,
    LOAN_PHASE_REVIEW,
    Loan,
    LoanLine,
    is_workflow_loan_phase,
)
from lamathek.models.material import MaterialType
from lamathek.models.user import User
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.loan_access import user_is_borrower
from lamathek.services.availability import assert_line_available
from lamathek.services.loans import loan_by_id
from lamathek.services.journal import append_journal, journal_line_action
from lamathek.services.loan_notifications import notify_loan_action
from lamathek.services.loan_workflow_steps import (
    assert_line_action_allowed,
    assert_loan_workflow_action,
    open_workflow_step_from_lines,
    sync_loan_phase_after_line_change,
    workflow_phase_for_gating,
)
from lamathek.timezone import instance_today


def line_is_terminal(line: LoanLine) -> bool:
    return line.status in LINE_STATUSES_TERMINAL


def _material_type_consumable(session: Session, line: LoanLine) -> bool:
    if line.material_type_id is None:
        return False
    mt = session.get(MaterialType, line.material_type_id)
    return bool(mt and mt.consumable)


def advance_loan_phase(session: Session, loan: Loan) -> None:
    if loan.phase == LOAN_PHASE_DRAFT:
        return
    if any(line.mail_pending for line in loan.lines):
        return
    if not loan.lines:
        loan.phase = LOAN_PHASE_CLOSED
        return
    for line in loan.lines:
        if not line_is_terminal(line):
            next_step = open_workflow_step_from_lines(loan)
            if next_step:
                loan.phase = next_step
            return
    loan.phase = LOAN_PHASE_CLOSED


def refresh_loan_phase(session: Session, loan: Loan) -> None:
    if loan.phase == LOAN_PHASE_DRAFT:
        return
    if not loan.lines:
        loan.phase = LOAN_PHASE_CLOSED
        return
    for line in loan.lines:
        if not line_is_terminal(line):
            if any(line.mail_pending for line in loan.lines):
                return
            if loan.phase == LOAN_PHASE_CLOSED:
                next_step = open_workflow_step_from_lines(loan)
                if next_step:
                    loan.phase = next_step
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


_STEP_OPEN_STATUS = {
    "review": LINE_STATUS_REQUESTED,
    "pack": LINE_STATUS_CONFIRMED,
    "handover": LINE_STATUS_PACKED,
    "return": LINE_STATUS_PICKED_UP,
    "restock": LINE_STATUS_RETURN_REPORTED,
}

_STEP_DONE_STATUS = {
    "review": LINE_STATUS_CONFIRMED,
    "pack": LINE_STATUS_PACKED,
    "handover": LINE_STATUS_PICKED_UP,
    "return": LINE_STATUS_RETURN_REPORTED,
    "restock": LINE_STATUS_RESTOCKED,
}

_STEP_MAIL_ACTION = {
    "review": "confirm",
    "pack": "pack",
    "handover": "pickup",
    "return": "report_return",
    "restock": "restock",
}


def _queue_mail(loan: Loan, lines: list[LoanLine]) -> None:
    for line in lines:
        line.mail_pending = True


def _mark_line_mail_pending(loan: Loan, line: LoanLine) -> None:
    del loan
    line.mail_pending = True


def _clear_mail(lines: list[LoanLine]) -> None:
    for line in lines:
        line.mail_pending = False


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
    loan.phase = LOAN_PHASE_REVIEW
    notified_lines = [line for line in loan.lines if line.id in notified_ids]
    _queue_mail(loan, notified_lines)
    session.flush()
    _complete_step_receipt(
        session,
        loan,
        actor=actor,
        action="request",
        line_ids=notified_ids,
    )
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
    _borrower_phone_required(loan.borrower_user)
    lines = _lines_for_loan(session, loan, line_ids)
    for line in lines:
        assert_line_action_allowed(loan, line, "confirm")
        if line.status != LINE_STATUS_REQUESTED:
            raise ValueError("invalid_line_status")
        # Checked line by line against the database, so lines confirmed earlier
        # in this call (flushed below) count as occupied for the next one.
        assert_line_available(session, loan, line)
        line.status = LINE_STATUS_CONFIRMED
        session.flush()
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="confirm"
        )
    if loan.phase == LOAN_PHASE_DRAFT:
        loan.phase = LOAN_PHASE_REVIEW
    _queue_mail(loan, lines)
    session.commit()
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
        assert_line_action_allowed(loan, line, "decline")
        line.status_before_end = line.status
        line.status = LINE_STATUS_UNAVAILABLE
        line.reason = reason.strip()
        _mark_line_mail_pending(loan, line)
        journal_line_action(
            session,
            actor=actor,
            loan_id=loan.id,
            line=line,
            action="decline",
            reason=line.reason,
        )
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
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
    assert_line_action_allowed(loan, original, "replace")
    if not reason.strip():
        raise ValueError("reason_required")
    new_line = _replacement_line(session, loan, original, replacement)

    original.status_before_end = original.status
    original.status = LINE_STATUS_UNAVAILABLE
    original.reason = reason.strip()
    _mark_line_mail_pending(loan, original)
    journal_line_action(
        session,
        actor=actor,
        loan_id=loan.id,
        line=original,
        action="replace",
        reason=original.reason,
    )
    session.flush()
    # The original no longer occupies anything; the replacement must fit the period.
    assert_line_available(session, loan, new_line)
    session.add(new_line)
    session.flush()
    _mark_line_mail_pending(loan, new_line)
    journal_line_action(
        session,
        actor=actor,
        loan_id=loan.id,
        line=new_line,
        action="replacement",
        replacesLineId=original.id,
    )
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def _replacement_line(
    session: Session, loan: Loan, original: LoanLine, replacement: dict
) -> LoanLine:
    """Validate what replaces ``original``: same Inventar, right tracking, a real change."""
    from lamathek.models.material import TRACKING_STOCK, Piece

    new_line = LoanLine(
        loan_id=loan.id,
        status=LINE_STATUS_CONFIRMED,
        replaces_line_id=original.id,
        mail_pending=False,
        origin_set_id=original.origin_set_id,
        origin_set_name=original.origin_set_name,
        origin_set_role=original.origin_set_role,
    )
    if "pieceId" in replacement:
        piece_id = replacement["pieceId"]
        piece = session.get(Piece, piece_id) if isinstance(piece_id, int) else None
        if piece is None or piece.material_type.inventory_id != loan.inventory_id:
            raise ValueError("invalid_piece")
        if piece_id == original.piece_id or any(
            line.piece_id == piece_id for line in loan.lines
        ):
            raise ValueError("line_exists")
        new_line.piece_id = piece_id
        return new_line
    if "materialTypeId" in replacement and "quantity" in replacement:
        material_type_id = replacement["materialTypeId"]
        quantity = replacement["quantity"]
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("invalid_quantity")
        material_type = (
            session.get(MaterialType, material_type_id)
            if isinstance(material_type_id, int)
            else None
        )
        if (
            material_type is None
            or material_type.inventory_id != loan.inventory_id
            or material_type.tracking != TRACKING_STOCK
        ):
            raise ValueError("invalid_material_type")
        new_line.material_type_id = material_type_id
        new_line.quantity = quantity
        return new_line
    raise ValueError("invalid_replacement")


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
        assert_line_action_allowed(loan, line, "withdraw")
        line.status = LINE_STATUS_WITHDRAWN
        _mark_line_mail_pending(loan, line)
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="withdraw"
        )
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
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
        assert_line_action_allowed(loan, line, "pack")
        if line.status != LINE_STATUS_CONFIRMED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_PACKED
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="pack"
        )
    _queue_mail(loan, lines)
    session.commit()
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
        assert_line_action_allowed(loan, line, "unpack")
        if line.status != LINE_STATUS_PACKED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_CONFIRMED
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="unpack"
        )
    _queue_mail(loan, lines)
    sync_loan_phase_after_line_change(loan)
    session.commit()
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
        assert_line_action_allowed(loan, line, "mark_not_packed")
        line.status_before_end = line.status
        line.status = LINE_STATUS_NOT_PACKED
        line.reason = reason.strip()
        _mark_line_mail_pending(loan, line)
        journal_line_action(
            session,
            actor=actor,
            loan_id=loan.id,
            line=line,
            action="not_packed",
            reason=line.reason,
        )
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
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
        assert_line_action_allowed(loan, line, "pickup")
        if line.status != LINE_STATUS_PACKED:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_PICKED_UP
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="pickup"
        )
    _queue_mail(loan, lines)
    session.commit()
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
        assert_line_action_allowed(loan, line, "undo_pickup")
        if line.status != LINE_STATUS_PICKED_UP:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_PACKED
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="undo_pickup"
        )
    _queue_mail(loan, lines)
    session.commit()
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
        assert_line_action_allowed(loan, line, "mark_not_picked_up")
        line.status_before_end = line.status
        line.status = LINE_STATUS_NOT_PICKED_UP
        line.reason = reason.strip()
        _mark_line_mail_pending(loan, line)
        journal_line_action(
            session,
            actor=actor,
            loan_id=loan.id,
            line=line,
            action="not_picked_up",
            reason=line.reason,
        )
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
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
        assert_line_action_allowed(loan, line, "report_return")
        if line.status != LINE_STATUS_PICKED_UP:
            raise ValueError("invalid_line_status")
        line.status = LINE_STATUS_RETURN_REPORTED
        journal_line_action(
            session, actor=actor, loan_id=loan.id, line=line, action="report_return"
        )
    _queue_mail(loan, lines)
    session.commit()
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


def _split_off(
    session: Session, loan: Loan, line: LoanLine, quantity: int, *, status: str, reason: str
) -> LoanLine:
    """Move ``quantity`` of a stock line onto a new line that ends with ``status``.

    The original keeps the rest and its status, so a partial loss or return
    never marks the whole Position and can be corrected on its own.
    """
    line.quantity = (line.quantity or 0) - quantity
    split = LoanLine(
        loan_id=loan.id,
        material_type_id=line.material_type_id,
        quantity=quantity,
        status=status,
        status_before_end=line.status,
        reason=reason,
        split_from_line_id=line.id,
        mail_pending=False,
    )
    _copy_line_origin(line, split)
    session.add(split)
    session.flush()
    _mark_line_mail_pending(loan, split)
    return split


def _end_as_not_returned(line: LoanLine, reason: str) -> None:
    line.status_before_end = line.status
    line.status = LINE_STATUS_NOT_RETURNED
    line.reason = reason


def _restock_stock_line(
    session: Session, loan: Loan, line: LoanLine, returned: int, entry: dict, *, actor: User
) -> list[int]:
    """Übernahme of a stock line. Consumables: the rest was used up (Verbrauch).
    Others: the rest is lost and split onto its own line (Verlust, D0009)."""
    from lamathek.models.material import STOCK_LOSS_CONSUMED
    from lamathek.services.stock_losses import book_stock_loss

    missing = line.quantity - returned
    if missing == 0:
        line.returned_quantity = returned
        line.status = LINE_STATUS_RESTOCKED
        journal_line_action(session, actor=actor, loan_id=loan.id, line=line, action="restock")
        return [line.id]
    if _material_type_consumable(session, line):
        reason = _reason_from_entry(entry) if returned == 0 else (entry.get("reason") or "")
        book_stock_loss(
            session,
            line.material_type_id,
            missing,
            kind=STOCK_LOSS_CONSUMED,
            loan_line_id=line.id,
            reason=reason,
        )
        line.returned_quantity = returned
        if returned == 0:
            _end_as_not_returned(line, reason)
            journal_line_action(
                session, actor=actor, loan_id=loan.id, line=line, action="restock_loss", reason=reason
            )
        else:
            line.status = LINE_STATUS_RESTOCKED
            journal_line_action(
                session, actor=actor, loan_id=loan.id, line=line, action="restock", consumed=missing
            )
        return [line.id]
    reason = _reason_from_entry(entry)
    if returned == 0:
        _end_as_not_returned(line, reason)
        line.returned_quantity = 0
        lost_line = line
        ids = [line.id]
    else:
        lost_line = _split_off(
            session, loan, line, missing, status=LINE_STATUS_NOT_RETURNED, reason=reason
        )
        line.returned_quantity = returned
        line.status = LINE_STATUS_RESTOCKED
        journal_line_action(session, actor=actor, loan_id=loan.id, line=line, action="restock")
        ids = [line.id, lost_line.id]
    book_stock_loss(session, line.material_type_id, missing, loan_line_id=lost_line.id, reason=reason)
    journal_line_action(
        session, actor=actor, loan_id=loan.id, line=lost_line, action="restock_loss", reason=reason
    )
    return ids


def restock_lines(
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
        if not isinstance(line_id, int):
            raise ValueError("invalid_entry")
        line = session.get(LoanLine, line_id)
        if line is None or line.loan_id != loan.id:
            raise ValueError("invalid_line")
        if line.status != LINE_STATUS_RETURN_REPORTED:
            raise ValueError("invalid_line_status")
        assert_line_action_allowed(loan, line, "restock")
        if line.piece_id is not None:
            line.status = LINE_STATUS_RESTOCKED
            journal_line_action(
                session, actor=actor, loan_id=loan.id, line=line, action="restock"
            )
            line_ids.append(line_id)
            continue
        if line.material_type_id is None or line.quantity is None:
            raise ValueError("invalid_line")
        returned = entry.get("returnedQuantity")
        if returned is None:
            returned = line.quantity
        if not isinstance(returned, int) or returned < 0 or returned > line.quantity:
            raise ValueError("invalid_entry")
        line_ids.extend(_restock_stock_line(session, loan, line, returned, entry, actor=actor))
    for line in loan.lines:
        if line.id in line_ids:
            _mark_line_mail_pending(loan, line)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
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

    from lamathek.services.piece_availability import create_total_loss_for_line
    from lamathek.services.stock_losses import book_stock_loss

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
        assert_line_action_allowed(loan, line, "record_loss")
        reason = _reason_from_entry(entry)
        if line.material_type_id is not None and line.quantity is not None:
            qty = line.quantity if quantity is None else quantity
            if not isinstance(qty, int) or qty <= 0 or qty > line.quantity:
                raise ValueError("invalid_quantity")
            if qty < line.quantity:
                # Only part is missing: the rest stays out and can still come back.
                lost = _split_off(
                    session, loan, line, qty, status=LINE_STATUS_NOT_RETURNED, reason=reason
                )
                book_stock_loss(
                    session, line.material_type_id, qty, loan_line_id=lost.id, reason=reason
                )
                journal_line_action(
                    session, actor=actor, loan_id=loan.id, line=lost, action="record_loss", reason=reason
                )
                line_ids.append(lost.id)
                continue
            book_stock_loss(
                session, line.material_type_id, qty, loan_line_id=line.id, reason=reason
            )
        _end_as_not_returned(line, reason)
        if line.piece_id is not None:
            create_total_loss_for_line(
                session,
                line,
                recorded_on=instance_today(),
                note=reason,
            )
        _mark_line_mail_pending(loan, line)
        journal_line_action(
            session,
            actor=actor,
            loan_id=loan.id,
            line=line,
            action="record_loss",
            reason=reason,
        )
        line_ids.append(line_id)
    session.commit()
    refresh_loan_phase(session, loan)
    session.commit()
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
    if not any(line.status == LINE_STATUS_DRAFT for line in loan.lines):
        # An empty request would sit in review with nothing to confirm.
        raise ValueError("empty_loan")
    _borrower_phone_required(borrower)
    loan.borrower_user_id = borrower_user_id
    loan.contact_user_id = actor.id
    if loan.pickup_on is None and loan.wish_pickup_on is not None:
        loan.pickup_on = loan.wish_pickup_on
    if (
        loan.return_on is None
        and loan.wish_return_on is not None
        and loan.kind != LOAN_KIND_PERMANENT
    ):
        loan.return_on = loan.wish_return_on
    loan.phase = LOAN_PHASE_REVIEW
    line_ids: list[int] = []
    for line in loan.lines:
        if line.status == LINE_STATUS_DRAFT:
            line.status = LINE_STATUS_REQUESTED
            line.request_notified = True
            line_ids.append(line.id)
    notified_lines = [line for line in loan.lines if line.id in line_ids]
    _queue_mail(loan, notified_lines)
    session.flush()
    if line_ids:
        _complete_step_receipt(
            session,
            loan,
            actor=actor,
            action="request",
            line_ids=line_ids,
        )
    else:
        session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def notify_added_lines(session: Session, loan: Loan, *, actor: User) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    if loan.phase == LOAN_PHASE_DRAFT:
        raise ValueError("invalid_loan_state")
    lines_to_notify = [
        line
        for line in loan.lines
        if line.status == LINE_STATUS_REQUESTED and not line.request_notified
    ]
    if not lines_to_notify:
        raise ValueError("empty_notify")
    for line in lines_to_notify:
        line.request_notified = True
    _queue_mail(loan, lines_to_notify)
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def _phase_for_complete(loan: Loan) -> str | None:
    phase = workflow_phase_for_gating(loan)
    if phase is not None:
        return phase
    if loan.phase == LOAN_PHASE_CLOSED and any(line.mail_pending for line in loan.lines):
        return open_workflow_step_from_lines(loan)
    return None


def _receipt_action(step: str | None, pending: list[LoanLine]) -> str:
    if step is None:
        return "changes"
    done = _STEP_DONE_STATUS[step]
    if pending and all(line.status == done for line in pending):
        return _STEP_MAIL_ACTION[step]
    return "changes"


def _complete_step_receipt(
    session: Session,
    loan: Loan,
    *,
    actor: User,
    action: str,
    line_ids: list[int],
    pdf_step: str | None = None,
) -> None:
    """Journal, queue the mails and advance the phase — all in one commit.

    ``pdf_step`` is the workflow step being closed, if any; its PDF list goes to
    the Materialwart*innen (closing review → Packliste, pack → Abholliste,
    handover → Rückgabeliste). A request or a cancellation attaches nothing.
    """
    from lamathek.services.loan_pdf import pdf_kind_for_mail_step

    mail_step = loan.phase if is_workflow_loan_phase(loan.phase) else None
    append_journal(
        session,
        "workflow.complete_step",
        actor,
        {
            "phase": loan.phase,
            "action": action,
            "mailStep": mail_step,
            "lineIds": line_ids,
        },
        loan_id=loan.id,
    )
    notify_loan_action(
        session,
        loan,
        action,
        actor=actor,
        line_ids=line_ids,
        mail_step=mail_step,
        pdf_kind=pdf_kind_for_mail_step(pdf_step),
    )
    pending = [line for line in loan.lines if line.mail_pending]
    _clear_mail(pending)
    advance_loan_phase(session, loan)
    session.commit()


def complete_loan_step(session: Session, loan: Loan, *, actor: User) -> Loan:
    step = _phase_for_complete(loan)
    can_manage = user_can_manage_inventory(session, actor, loan.inventory)
    can_share = _actor_is_borrower_or_manager(session, actor, loan)
    if step in {"review", "pack", "restock"}:
        if not can_manage:
            raise ValueError("forbidden")
    elif not can_share:
        raise ValueError("forbidden")

    if step is not None and step in _STEP_OPEN_STATUS:
        open_status = _STEP_OPEN_STATUS[step]
        if any(line.status == open_status for line in loan.lines):
            raise ValueError("step_incomplete")
    if step == "pack" and any(line.status == LINE_STATUS_REQUESTED for line in loan.lines):
        raise ValueError("step_incomplete")

    pending = [line for line in loan.lines if line.mail_pending]
    if not pending:
        raise ValueError("empty_step")

    _complete_step_receipt(
        session,
        loan,
        actor=actor,
        action=_receipt_action(step, pending),
        line_ids=[line.id for line in pending],
        pdf_step=step,
    )
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


_HANDED_OUT_STATUSES = frozenset(
    {
        LINE_STATUS_PICKED_UP,
        LINE_STATUS_RETURN_REPORTED,
        LINE_STATUS_RESTOCKED,
        LINE_STATUS_NOT_RETURNED,
    }
)


def delete_unreleased_loan(session: Session, loan: Loan, *, actor: User) -> None:
    """Borrowers delete their drafts; superusers any Verleih whose material never
    went out. Once something was handed over, the record (losses, journal) stays."""
    if actor.is_superuser:
        if any(line.status in _HANDED_OUT_STATUSES for line in loan.lines):
            raise ValueError("invalid_loan_state")
        session.delete(loan)
        session.commit()
        return
    _require_borrower(actor, loan)
    if loan.phase != LOAN_PHASE_DRAFT:
        raise ValueError("invalid_loan_state")
    session.delete(loan)
    session.commit()


def cancel_unpacked_loan(session: Session, loan: Loan, *, actor: User) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    if not is_workflow_loan_phase(loan.phase):
        raise ValueError("invalid_loan_state")
    if any(line.status in _CANCEL_FORBIDDEN_LINE_STATUSES for line in loan.lines):
        raise ValueError("invalid_loan_state")
    withdrawn_ids: list[int] = []
    for line in loan.lines:
        if line.status in _CANCEL_WITHDRAW_LINE_STATUSES:
            line.status = LINE_STATUS_WITHDRAWN
            _mark_line_mail_pending(loan, line)
            withdrawn_ids.append(line.id)
    if not loan.lines:
        loan.phase = LOAN_PHASE_CLOSED
    session.flush()
    refresh_loan_phase(session, loan)
    if not loan.lines and loan.phase != LOAN_PHASE_CLOSED:
        loan.phase = LOAN_PHASE_CLOSED
    session.flush()
    if not withdrawn_ids:
        session.commit()
    if withdrawn_ids:
        _complete_step_receipt(
            session,
            loan,
            actor=actor,
            action="cancel",
            line_ids=withdrawn_ids,
        )
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def skip_pickup_to_return(session: Session, loan: Loan, *, actor: User) -> Loan:
    if not _actor_is_borrower_or_manager(session, actor, loan):
        raise ValueError("forbidden")
    assert_loan_workflow_action(loan, "skip_pickup")
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
            _mark_line_mail_pending(loan, line)
            line_ids.append(line.id)
    session.flush()
    refresh_loan_phase(session, loan)
    session.flush()
    if line_ids:
        _complete_step_receipt(
            session,
            loan,
            actor=actor,
            action="skip_pickup",
            line_ids=line_ids,
        )
    return loan_by_id(session, loan.id)  # type: ignore[return-value]

