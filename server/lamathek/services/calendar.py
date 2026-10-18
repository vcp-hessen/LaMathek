"""Kalender-Einträge und iCal-Feeds."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.calendar import (
    CALENDAR_SCOPE_BORROWER,
    CALENDAR_SCOPE_CONTACT,
    CALENDAR_SCOPE_INVENTORY,
    CalendarFeed,
)
from lamathek.models.loan import LOAN_KIND_PERMANENT, LOAN_PHASE_DRAFT, Loan
from lamathek.models.user import User
from lamathek.services.inventories import inventory_by_id, user_can_manage_inventory
from lamathek.services.loan_access import user_can_view_loan
from lamathek.services.loan_display import (
    ics_loan_description,
    ics_text_escape,
    loan_display_title,
    loan_detail_url,
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_calendar_feed(
    session: Session,
    user: User,
    *,
    label: str,
    scope: str,
    inventory_id: int | None = None,
) -> tuple[CalendarFeed, str]:
    if scope == CALENDAR_SCOPE_BORROWER:
        inventory_id = None
    elif scope == CALENDAR_SCOPE_CONTACT:
        if inventory_id is None:
            raise ValueError("inventory_required")
        if inventory_by_id(session, inventory_id) is None:
            raise ValueError("not_found")
    elif scope == CALENDAR_SCOPE_INVENTORY:
        if inventory_id is None:
            raise ValueError("inventory_required")
        inventory = inventory_by_id(session, inventory_id)
        if inventory is None:
            raise ValueError("not_found")
        assert_inventory_calendar(session, user, inventory)
    else:
        raise ValueError("invalid_scope")

    token = secrets.token_urlsafe(24)
    feed = CalendarFeed(
        user_id=user.id,
        scope=scope,
        inventory_id=inventory_id,
        label=label.strip(),
        token_hash=_hash_token(token),
    )
    session.add(feed)
    session.commit()
    session.refresh(feed)
    return feed, token


def list_calendar_feeds(session: Session, user: User) -> list[CalendarFeed]:
    return list(
        session.scalars(
            select(CalendarFeed)
            .where(CalendarFeed.user_id == user.id)
            .order_by(CalendarFeed.created_at.desc())
        ).all()
    )


def delete_calendar_feed(session: Session, user: User, feed_id: int) -> bool:
    feed = session.get(CalendarFeed, feed_id)
    if feed is None or feed.user_id != user.id:
        return False
    if feed.scope == CALENDAR_SCOPE_INVENTORY and feed.inventory_id is not None:
        inventory = inventory_by_id(session, feed.inventory_id)
        if inventory is None:
            return False
        try:
            assert_inventory_calendar(session, user, inventory)
        except ValueError:
            return False
    session.delete(feed)
    session.commit()
    return True


def calendar_feed_ics_path(feed: CalendarFeed) -> str:
    """Öffentlicher Pfad (ohne Token) — beschreibt den Abo-Inhalt."""
    if feed.scope == CALENDAR_SCOPE_BORROWER:
        return "/api/calendar/ics/borrower.ics"
    if feed.scope == CALENDAR_SCOPE_CONTACT:
        if feed.inventory_id is None:
            raise ValueError("invalid_feed")
        return f"/api/calendar/ics/inventories/{feed.inventory_id}/contact.ics"
    if feed.scope == CALENDAR_SCOPE_INVENTORY:
        if feed.inventory_id is None:
            raise ValueError("invalid_feed")
        return f"/api/calendar/ics/inventories/{feed.inventory_id}/all-loans.ics"
    raise ValueError("invalid_scope")


def calendar_feed_ics_url(feed: CalendarFeed, token: str) -> str:
    return f"{calendar_feed_ics_path(feed)}?{urlencode({'token': token})}"


def feed_matches_ics_route(
    feed: CalendarFeed,
    scope: str,
    inventory_id: int | None,
) -> bool:
    if feed.scope != scope:
        return False
    if scope == CALENDAR_SCOPE_BORROWER:
        return feed.inventory_id is None
    return feed.inventory_id == inventory_id


def calendar_feed_to_json(session: Session, feed: CalendarFeed) -> dict:
    inventory_name = ""
    if feed.inventory_id is not None:
        inventory = inventory_by_id(session, feed.inventory_id)
        inventory_name = inventory.name if inventory else ""
    return {
        "id": feed.id,
        "label": feed.label,
        "scope": feed.scope,
        "inventoryId": feed.inventory_id,
        "inventoryName": inventory_name,
        "createdAt": feed.created_at.isoformat() if feed.created_at else None,
    }


def feed_by_token(session: Session, token: str) -> CalendarFeed | None:
    return session.scalar(
        select(CalendarFeed).where(CalendarFeed.token_hash == _hash_token(token))
    )


def _loan_query():
    return select(Loan).options(
        selectinload(Loan.inventory),
        selectinload(Loan.group),
        selectinload(Loan.event),
        selectinload(Loan.borrower_user),
    )


def loans_for_borrower_calendar(session: Session, user: User) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(
                Loan.phase != LOAN_PHASE_DRAFT,
                Loan.pickup_on.is_not(None),
                Loan.borrower_user_id == user.id,
            )
            .order_by(Loan.pickup_on)
        ).all()
    )


def loans_for_contact_calendar(session: Session, user: User) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(
                Loan.phase != LOAN_PHASE_DRAFT,
                Loan.pickup_on.is_not(None),
                Loan.contact_user_id == user.id,
            )
            .order_by(Loan.pickup_on)
        ).all()
    )


def loans_for_contact_in_inventory(
    session: Session, user: User, inventory_id: int
) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(
                Loan.inventory_id == inventory_id,
                Loan.phase != LOAN_PHASE_DRAFT,
                Loan.pickup_on.is_not(None),
                Loan.contact_user_id == user.id,
            )
            .order_by(Loan.pickup_on)
        ).all()
    )


def loans_for_feed(session: Session, feed: CalendarFeed, owner: User) -> list[Loan]:
    if feed.scope in (CALENDAR_SCOPE_BORROWER, "user"):
        return loans_for_borrower_calendar(session, owner)
    if feed.scope == CALENDAR_SCOPE_CONTACT and feed.inventory_id is not None:
        return loans_for_contact_in_inventory(session, owner, feed.inventory_id)
    if feed.scope == CALENDAR_SCOPE_INVENTORY and feed.inventory_id is not None:
        return loans_for_inventory_calendar(session, feed.inventory_id)
    return []


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
        "title": loan_display_title(loan),
        "phase": loan.phase,
        "pickupOn": loan.pickup_on.isoformat() if loan.pickup_on else None,
        "returnOn": end.isoformat() if end else None,
        "permanent": permanent,
        "asBorrower": viewer_id is not None and loan.borrower_user_id == viewer_id,
        "asContact": viewer_id is not None and loan.contact_user_id == viewer_id,
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
        title = loan_display_title(loan)
        if loan.kind == LOAN_KIND_PERMANENT:
            title = f"Dauerleihgabe: {title}"
        summary = ics_text_escape(title)
        event_lines = [
            "BEGIN:VEVENT",
            f"UID:loan-{loan.id}@lamathek",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{dtend.strftime('%Y%m%d')}",
            f"SUMMARY:{summary}",
        ]
        description = ics_loan_description(loan)
        if description:
            event_lines.append(f"DESCRIPTION:{description}")
        detail_url = loan_detail_url(loan)
        if detail_url:
            event_lines.append(f"URL:{detail_url}")
        event_lines.append("END:VEVENT")
        lines.extend(event_lines)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def visible_calendar_loans(session: Session, user: User, loans: list[Loan]) -> list[Loan]:
    return [loan for loan in loans if user_can_view_loan(session, user, loan)]


def assert_inventory_calendar(session: Session, user: User, inventory) -> None:
    if not user_can_manage_inventory(session, user, inventory):
        raise ValueError("forbidden")
