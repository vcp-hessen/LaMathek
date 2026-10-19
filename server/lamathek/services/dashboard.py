"""Startseiten-Karten über alle sichtbaren Inventare."""

from __future__ import annotations


from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session, selectinload

from lamathek.models.loan import (
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_DRAFT,
    LOAN_PHASE_HANDOVER,
    LOAN_PHASE_PACK,
    LOAN_PHASE_RESTOCK,
    LOAN_PHASE_RETURN,
    LOAN_PHASE_REVIEW,
    Loan,
    LoanLine,
)
from lamathek.models.mail import OUTBOX_FAILED, OUTBOX_PENDING, MailOutbox
from lamathek.services.loan_conflicts import enrich_loan_detail_warnings
from lamathek.services.loan_display import loan_display_title
from lamathek.models.user import User
from lamathek.services.inventories import list_inventories_for_user, user_can_manage_inventory
from lamathek.timezone import instance_today


# Warnings that stop a confirmation or mean material is missing (not mere hints).
_CONFLICT_CODES = frozenset(
    {
        "piece_booked",
        "piece_overdue",
        "stock_short",
        "piece_retired",
        "piece_total_loss",
        "piece_severe_damage",
    }
)


def _summary(loan: Loan) -> dict:
    return {
        "id": loan.id,
        "inventoryId": loan.inventory_id,
        "inventoryName": loan.inventory.name if loan.inventory else "",
        "title": loan_display_title(loan),
        "phase": loan.phase,
        "returnOn": loan.return_on.isoformat() if loan.return_on else None,
    }


def _has_conflict(session: Session, loan: Loan) -> bool:
    flat, _ = enrich_loan_detail_warnings(session, loan)
    return any(w["code"] in _CONFLICT_CODES for w in flat)


def _loans_with_stuck_mail(session: Session, loan_ids: list[int]) -> set[int]:
    if not loan_ids:
        return set()
    rows = session.scalars(
        select(MailOutbox.loan_id).where(
            MailOutbox.loan_id.in_(loan_ids),
            or_(
                MailOutbox.status == OUTBOX_FAILED,
                (MailOutbox.status == OUTBOX_PENDING) & (MailOutbox.attempts > 0),
            ),
        )
    ).all()
    return set(rows)


def build_dashboard(session: Session, user: User) -> dict:
    inventories = list_inventories_for_user(session, user)
    managed_ids = [
        inv.id for inv in inventories if user_can_manage_inventory(session, user, inv)
    ]
    # Only open Verleihe the user borrows or manages, filtered in the database.
    involved = Loan.borrower_user_id == user.id
    if user.is_superuser:
        involved = true()
    elif managed_ids:
        involved = or_(involved, Loan.inventory_id.in_(managed_ids))
    loans = list(
        session.scalars(
            select(Loan)
            .options(
                selectinload(Loan.inventory),
                selectinload(Loan.group),
                selectinload(Loan.event),
                selectinload(Loan.lines).selectinload(LoanLine.piece),
                selectinload(Loan.lines).selectinload(LoanLine.material_type),
            )
            .where(Loan.phase.not_in((LOAN_PHASE_DRAFT, LOAN_PHASE_CLOSED)), involved)
            .order_by(Loan.pickup_on, Loan.id)
        ).all()
    )
    today = instance_today()
    cards: dict[str, list[dict]] = {
        "waiting": [],
        "openRequests": [],
        "conflicts": [],
        "returnsDue": [],
        "overdue": [],
        "openActions": [],
        "stuckMails": [],
        "myLoans": [],
    }
    managed_loans = [
        loan for loan in loans if user.is_superuser or loan.inventory_id in managed_ids
    ]
    stuck = _loans_with_stuck_mail(session, [loan.id for loan in managed_loans])
    for loan in loans:
        if loan.borrower_user_id == user.id:
            cards["myLoans"].append(_summary(loan))
    for loan in managed_loans:
        if loan.phase in {LOAN_PHASE_REVIEW, LOAN_PHASE_PACK, LOAN_PHASE_HANDOVER, LOAN_PHASE_RESTOCK}:
            cards["waiting"].append(_summary(loan))
        if loan.phase == LOAN_PHASE_REVIEW:
            cards["openRequests"].append(_summary(loan))
        if loan.phase == LOAN_PHASE_RETURN and loan.return_on is not None:
            if loan.return_on <= today:
                cards["returnsDue"].append(_summary(loan))
            if loan.return_on < today:
                cards["overdue"].append(_summary(loan))
        if any(line.mail_pending for line in loan.lines):
            cards["openActions"].append(_summary(loan))
        if loan.id in stuck:
            cards["stuckMails"].append(_summary(loan))
        if loan.phase in {LOAN_PHASE_REVIEW, LOAN_PHASE_PACK, LOAN_PHASE_HANDOVER} and _has_conflict(
            session, loan
        ):
            cards["conflicts"].append(_summary(loan))

    return {
        "welcomeName": user.name or user.email or "",
        "cards": cards,
        "canManage": bool(managed_ids) or user.is_superuser,
    }
