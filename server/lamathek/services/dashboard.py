"""Startseiten-Karten über alle sichtbaren Inventare."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
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
)
from lamathek.models.user import User
from lamathek.services.inventories import list_inventories_for_user, user_can_manage_inventory


def _summary(loan: Loan) -> dict:
    return {
        "id": loan.id,
        "inventoryId": loan.inventory_id,
        "inventoryName": loan.inventory.name if loan.inventory else "",
        "title": loan.group.name if loan.group else "",
        "phase": loan.phase,
        "returnOn": loan.return_on.isoformat() if loan.return_on else None,
    }


def build_dashboard(session: Session, user: User) -> dict:
    inventories = list_inventories_for_user(session, user)
    managed_ids = [
        inv.id for inv in inventories if user_can_manage_inventory(session, user, inv)
    ]
    loans = list(
        session.scalars(
            select(Loan)
            .options(selectinload(Loan.inventory), selectinload(Loan.group), selectinload(Loan.lines))
            .where(Loan.phase != LOAN_PHASE_DRAFT)
        ).all()
    )
    today = date.today()
    waiting = []
    returns_due = []
    overdue = []
    my_loans = []
    open_requests = []
    open_actions = []
    for loan in loans:
        if loan.borrower_user_id == user.id and loan.phase != LOAN_PHASE_CLOSED:
            my_loans.append(_summary(loan))
        manages = loan.inventory_id in managed_ids or user.is_superuser
        if not manages and loan.borrower_user_id != user.id and loan.contact_user_id != user.id:
            continue
        if manages and loan.phase in {
            LOAN_PHASE_REVIEW,
            LOAN_PHASE_PACK,
            LOAN_PHASE_HANDOVER,
            LOAN_PHASE_RESTOCK,
        }:
            waiting.append(_summary(loan))
        if manages and loan.phase == LOAN_PHASE_REVIEW:
            open_requests.append(_summary(loan))
        if manages and loan.phase == LOAN_PHASE_RETURN and loan.return_on is not None:
            if loan.return_on <= today:
                returns_due.append(_summary(loan))
            if loan.return_on < today:
                overdue.append(_summary(loan))
        if manages and any(line.mail_pending for line in loan.lines):
            open_actions.append(_summary(loan))

    return {
        "welcomeName": user.name or user.email or "",
        "cards": {
            "waiting": waiting,
            "returnsDue": returns_due,
            "overdue": overdue,
            "myLoans": my_loans,
            "openRequests": open_requests,
            "openActions": open_actions,
        },
        "canManage": bool(managed_ids) or user.is_superuser,
    }
