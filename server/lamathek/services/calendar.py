"""Kalender-Einträge und iCal-Feeds."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.calendar import CALENDAR_SCOPE_INVENTORY, CALENDAR_SCOPE_USER, CalendarFeed
from lamathek.models.loan import LOAN_KIND_PERMANENT, LOAN_PHASE_DRAFT, Loan
from lamathek.models.user import User
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.loan_access import user_can_view_loan


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_feed_token(
    session: Session,
    user: User,
    *,
    scope: str,
    inventory_id: int | None = None,
) -> str:
    existing = session.scalar(
        select(CalendarFeed).where(
            CalendarFeed.user_id == user.id,
            CalendarFeed.scope == scope,
            CalendarFeed.inventory_id == inventory_id,
        )
    )
    token = secrets.token_urlsafe(24)
    digest = _hash_token(token)
    if existing is None:
        session.add(
            CalendarFeed(
                user_id=user.id,
                scope=scope,
                inventory_id=inventory_id,
                token_hash=digest,
            )
        )
    else:
        existing.token_hash = digest
    session.commit()
    return token


def revoke_feed(
    session: Session, user: User, *, scope: str, inventory_id: int | None = None
) -> None:
    row = session.scalar(
        select(CalendarFeed).where(
            CalendarFeed.user_id == user.id,
            CalendarFeed.scope == scope,
            CalendarFeed.inventory_id == inventory_id,
        )
    )
    if row is not None:
        session.delete(row)
        session.commit()


def feed_by_token(session: Session, token: str) -> CalendarFeed | None:
    return session.scalar(
        select(CalendarFeed).where(CalendarFeed.token_hash == _hash_token(token))
    )


def _loan_query():
    return select(Loan).options(
        selectinload(Loan.inventory),
        selectinload(Loan.group),
        selectinload(Loan.borrower_user),
    )


def loans_for_user_calendar(session: Session, user: User) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(
                Loan.phase != LOAN_PHASE_DRAFT,
                Loan.pickup_on.is_not(None),
                or_(
                    Loan.borrower_user_id == user.id,
                    Loan.contact_user_id == user.id,
                ),
            )
            .order_by(Loan.pickup_on)
        ).all()
    )


def loans_for_inventory_calendar(
    session: Session, inventory_id: int
) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(
                Loan.inventory_id == inventory_id,
                Loan.phase != LOAN_PHASE_DRAFT,
                Loan.pickup_on.is_not(None),
            )
            .order_by(Loan.pickup_on)
        ).all()
    )


def loan_to_calendar_item(loan: Loan, *, viewer_id: int | None) -> dict:
    end = loan.return_on
    permanent = loan.kind == LOAN_KIND_PERMANENT or end is None
    return {
        "loanId": loan.id,
        "inventoryId": loan.inventory_id,
        "inventoryName": loan.inventory.name if loan.inventory else "",
        "title": loan.group.name if loan.group else f"Verleih {loan.id}",
        "phase": loan.phase,
        "pickupOn": loan.pickup_on.isoformat() if loan.pickup_on else None,
        "returnOn": end.isoformat() if end else None,
        "permanent": permanent,
        "mine": viewer_id is not None and loan.contact_user_id == viewer_id,
    }


def ics_for_loans(loans: list[Loan]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LaMathek//Kalender//DE",
        "CALSCALE:GREGORIAN",
    ]
    for loan in loans:
        if loan.pickup_on is None:
            continue
        start = loan.pickup_on
        end = loan.return_on or (start + timedelta(days=1))
        # iCal DTEND is exclusive
        dtend = end + timedelta(days=1)
        title = loan.group.name if loan.group else f"Verleih {loan.id}"
        if loan.kind == LOAN_KIND_PERMANENT:
            title = f"Dauerleihgabe: {title}"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:loan-{loan.id}@lamathek",
                f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{dtend.strftime('%Y%m%d')}",
                f"SUMMARY:{title}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def visible_calendar_loans(session: Session, user: User, loans: list[Loan]) -> list[Loan]:
    return [loan for loan in loans if user_can_view_loan(session, user, loan)]


def assert_inventory_calendar(session: Session, user: User, inventory) -> None:
    if not user_can_manage_inventory(session, user, inventory):
        raise ValueError("forbidden")
