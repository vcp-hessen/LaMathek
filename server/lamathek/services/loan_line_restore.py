"""Re-open reasoned terminal loan lines (keep workflow gating in loan_workflow_steps)."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from lamathek.models.loan import (
    LINE_STATUS_NOT_RETURNED,
    LINE_STATUSES_BLOCKING,
    LINE_STATUS_UNAVAILABLE,
    LINE_STATUS_WITHDRAWN,
    LINE_STATUSES_TERMINAL,
    LOAN_PHASE_CLOSED,
    Loan,
    LoanLine,
)
from lamathek.models.user import User
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.loan_workflow import refresh_loan_phase
from lamathek.services.loan_workflow_steps import (
    RESTORABLE_TERMINAL_STATUSES,
    assert_line_action_allowed,
    open_workflow_step_from_lines,
    restore_target_status,
    sync_loan_phase_after_line_change,
)
from lamathek.services.journal import journal_line_action
from lamathek.services.availability import assert_line_available, line_interval
from lamathek.services.loans import loan_by_id, restore_withdrawn_line
from lamathek.services.stock_losses import cancel_line_losses
from lamathek.timezone import instance_today


def _replacement_blocks_reopen(loan: Loan, line: LoanLine) -> bool:
    for other in loan.lines:
        if other.id == line.id or other.replaces_line_id != line.id:
            continue
        if other.status not in LINE_STATUSES_TERMINAL:
            return True
    return False


def _validate_target_availability(session: Session, loan: Loan, line: LoanLine, target: str) -> None:
    """Every restore that makes the line occupy material again is checked, not only
    the one back to „bestätigt“: the piece may have been lent out meanwhile."""
    if target not in LINE_STATUSES_BLOCKING:
        return
    # The period depends on the status the line returns to (overdue lines extend to today).
    as_restored = SimpleNamespace(status=target)
    assert_line_available(session, loan, line, interval=line_interval(loan, as_restored))


def restore_loan_line(session: Session, loan: Loan, line_id: int, *, actor: User) -> Loan:
    line = session.get(LoanLine, line_id)
    if line is None or line.loan_id != loan.id:
        raise ValueError("invalid_line")

    if line.status == LINE_STATUS_WITHDRAWN:
        return restore_withdrawn_line(session, loan, line_id, actor=actor)

    if line.status not in RESTORABLE_TERMINAL_STATUSES:
        raise ValueError("invalid_line_status")

    if not user_can_manage_inventory(session, actor, loan.inventory):
        raise ValueError("forbidden")

    assert_line_action_allowed(loan, line, "restore")

    if line.status == LINE_STATUS_UNAVAILABLE and _replacement_blocks_reopen(loan, line):
        raise ValueError("replacement_blocks_reopen")

    target = restore_target_status(line)
    if target is None:
        raise ValueError("invalid_line_status")

    # Undo the loss first (stock events, or the piece's total loss): that alone
    # frees the material again, so the availability check below sees it.
    if line.material_type_id is not None:
        cancel_line_losses(session, line.id, actor=actor)
    if line.status == LINE_STATUS_NOT_RETURNED:
        from lamathek.services.piece_availability import cancel_total_loss_for_line

        if line.piece_id is not None:
            cancel_total_loss_for_line(
                session,
                line.id,
                recorded_on=instance_today(),
                note="Korrektur Verlust",
            )
        line.returned_quantity = None
    session.flush()
    try:
        _validate_target_availability(session, loan, line, target)
    except ValueError:
        session.rollback()
        raise

    line.status = target
    line.status_before_end = None
    line.reason = ""
    line.mail_pending = True
    journal_line_action(
        session, actor=actor, loan_id=loan.id, line=line, action="restore"
    )

    was_closed = loan.phase == LOAN_PHASE_CLOSED
    sync_loan_phase_after_line_change(loan)
    if was_closed:
        next_step = open_workflow_step_from_lines(loan)
        if next_step:
            loan.phase = next_step
    session.flush()
    refresh_loan_phase(session, loan)
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]
