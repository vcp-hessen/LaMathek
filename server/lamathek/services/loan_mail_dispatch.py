"""Rollenspezifischer Versand von Verleih-Mails (kein CC zwischen Ausleihende*r und MW)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from lamathek.models.loan import Loan
from lamathek.models.user import User
from lamathek.services.inventories import permission_users, user_can_manage_inventory
from lamathek.services.mail import is_valid_email
from lamathek.services.mail_templates import render_loan_action_mail

Audience = Literal["borrower", "managers"]

_LOAN_MAIL_AUDIENCES: tuple[Audience, ...] = ("borrower", "managers")


@dataclass(frozen=True)
class MailRecipients:
    to: str
    cc: list[str]


def _user_email(user: User | None) -> str | None:
    if user is None:
        return None
    email = (user.email or "").strip()
    if email and is_valid_email(email):
        return email
    return None


def _manager_emails(session: Session, inventory_id: int) -> list[str]:
    from lamathek.services.inventories import inventory_by_id

    inventory = inventory_by_id(session, inventory_id)
    users = permission_users(session, inventory.id) if inventory else []
    return [
        u.email.strip()
        for u in users
        if u.email and is_valid_email(u.email.strip())
    ]


def _dedupe_cc(to: str, cc: list[str]) -> list[str]:
    seen = {to.lower()}
    result: list[str] = []
    for addr in cc:
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(addr)
    return result


def recipients_for_audience(
    session: Session,
    loan: Loan,
    audience: Audience,
) -> MailRecipients | None:
    if audience == "borrower":
        email = _user_email(loan.borrower_user)
        if email is None:
            return None
        return MailRecipients(to=email, cc=[])

    managers = _manager_emails(session, loan.inventory_id)
    if not managers:
        return None

    contact = _user_email(loan.contact_user)
    if contact and contact.lower() in {m.lower() for m in managers}:
        to = contact
        cc = [addr for addr in managers if addr.lower() != to.lower()]
    else:
        to = managers[0]
        cc = managers[1:]

    return MailRecipients(to=to, cc=_dedupe_cc(to, cc))


def variant_for_action(
    session: Session,
    loan: Loan,
    actor: User,
    action: str,
    audience: Audience,
) -> str:
    del audience
    if action not in {"request", "added"}:
        return ""
    if not user_can_manage_inventory(session, actor, loan.inventory):
        return ""
    if (
        loan.contact_user_id is not None
        and loan.contact_user_id != loan.borrower_user_id
    ):
        return "FromManager"
    return ""


def dispatch_loan_mail(
    session: Session,
    loan: Loan,
    action: str,
    line_ids: list[int],
    *,
    actor: User,
    mail_step: str | None = None,
    locale: str = "de",
) -> None:
    from lamathek.services.loan_notifications import get_mail_sender

    sender = get_mail_sender()
    for audience in _LOAN_MAIL_AUDIENCES:
        recipients = recipients_for_audience(session, loan, audience)
        if recipients is None:
            continue
        variant = variant_for_action(session, loan, actor, action, audience)
        subject, text, html = render_loan_action_mail(
            session,
            loan,
            action,
            line_ids,
            actor=actor,
            audience=audience,
            variant=variant,
            locale=locale,
            mail_step=mail_step,
        )
        sender(recipients.to, subject, text, html, recipients.cc)
