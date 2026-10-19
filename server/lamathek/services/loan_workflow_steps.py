"""Verleih workflow step derivation and action gating (lamathek/domain/workflow_gates.json)."""

from __future__ import annotations

from lamathek.models.loan import (
    LINE_STATUS_DRAFT,
    LINE_STATUS_WITHDRAWN,
    LINE_STATUSES_TERMINAL,
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_DRAFT,
    WORKFLOW_LOAN_PHASES,
    Loan,
    LoanLine,
    is_workflow_loan_phase,
)
from lamathek.services.workflow_gates import (
    line_action_steps,
    workflow_gates,
    open_workflow_step_from_open_statuses,
    workflow_step_for_line_status as _step_for_status,
)

_RESTORE = workflow_gates()["restore"]
# Shared with web/src/domain/loanWorkflowSteps.ts through workflow_gates.json.
_RESTORE_TARGET_FALLBACK: dict[str, str] = dict(_RESTORE["fallbackTarget"])
RESTORABLE_TERMINAL_STATUSES = frozenset(_RESTORE_TARGET_FALLBACK)
_RESTORE_VALID_TARGETS = frozenset(_RESTORE["validTargets"])

WORKFLOW_STEPS = WORKFLOW_LOAN_PHASES

_WORKFLOW_PHASE_ORDER = (
    "review",
    "pack",
    "handover",
    "return",
    "restock",
)


def _workflow_phase_rank(phase: str) -> int:
    return _WORKFLOW_PHASE_ORDER.index(phase)

_HANDOVER_OR_LATER = frozenset(workflow_gates()["handoverOrLaterStatuses"])


def open_workflow_step_from_lines(loan: Loan) -> str | None:
    open_statuses = {
        line.status for line in loan.lines if line.status not in LINE_STATUSES_TERMINAL
    }
    return open_workflow_step_from_open_statuses(open_statuses)


def open_workflow_step(loan: Loan) -> str | None:
    if loan.phase in (LOAN_PHASE_DRAFT, LOAN_PHASE_CLOSED):
        return None
    return open_workflow_step_from_lines(loan)


def workflow_phase_for_gating(loan: Loan) -> str | None:
    if is_workflow_loan_phase(loan.phase):
        return loan.phase
    return None


def loan_past_handover(loan: Loan) -> bool:
    return any(line.status in _HANDOVER_OR_LATER for line in loan.lines)


def workflow_step_for_line_status(status: str) -> str | None:
    return _step_for_status(status)


def restore_target_status(line: LoanLine) -> str | None:
    prior = line.status_before_end
    if prior in _RESTORE_VALID_TARGETS:
        return prior
    return _RESTORE_TARGET_FALLBACK.get(line.status)


def action_workflow_step(action: str, line: LoanLine, loan: Loan) -> str | None:
    status = line.status

    if action == "restore":
        if status in RESTORABLE_TERMINAL_STATUSES:
            target = restore_target_status(line)
            if target is None:
                return None
            return workflow_step_for_line_status(target)
        if status != LINE_STATUS_WITHDRAWN or loan_past_handover(loan):
            return None
        phase = workflow_phase_for_gating(loan)
        if phase in ("review", "pack"):
            return phase
        return None
    if action == "remove":
        return "draft" if status == LINE_STATUS_DRAFT else None

    steps = line_action_steps(action, status)
    if not steps:
        return None
    return steps[0]


def allowed_workflow_steps(action: str, line: LoanLine, loan: Loan) -> frozenset[str]:
    if action == "restore":
        required = action_workflow_step(action, line, loan)
        if required is None:
            return frozenset()
        return frozenset({required})
    steps = line_action_steps(action, line.status)
    if not steps:
        return frozenset()
    return frozenset(steps)


def assert_line_action_allowed(loan: Loan, line: LoanLine, action: str) -> None:
    if action == "remove":
        if loan.phase == LOAN_PHASE_DRAFT and line.status == LINE_STATUS_DRAFT:
            return
        raise ValueError("workflow_step_mismatch")

    allowed = allowed_workflow_steps(action, line, loan)
    if not allowed:
        raise ValueError("workflow_step_mismatch")

    if action == "restore" and line.status in RESTORABLE_TERMINAL_STATUSES:
        if loan.phase == LOAN_PHASE_CLOSED:
            return
        return

    phase = workflow_phase_for_gating(loan)
    if phase is None:
        raise ValueError("workflow_step_mismatch")

    if phase not in allowed:
        raise ValueError("workflow_step_mismatch")


def sync_loan_phase_after_line_change(loan: Loan) -> None:
    """Pull loan.phase back when line states regress; never skip forward (use advance_loan_phase)."""
    if loan.phase in (LOAN_PHASE_DRAFT, LOAN_PHASE_CLOSED):
        return
    open_step = open_workflow_step_from_lines(loan)
    if open_step is None:
        if not any(line.mail_pending for line in loan.lines):
            loan.phase = LOAN_PHASE_CLOSED
        return
    if not is_workflow_loan_phase(loan.phase):
        loan.phase = open_step
        return
    if _workflow_phase_rank(open_step) < _workflow_phase_rank(loan.phase):
        loan.phase = open_step


def assert_loan_workflow_action(loan: Loan, action: str) -> None:
    if action == "skip_pickup":
        if workflow_phase_for_gating(loan) != "handover":
            raise ValueError("workflow_step_mismatch")
        return
    raise ValueError("workflow_step_mismatch")
