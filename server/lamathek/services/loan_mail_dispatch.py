"""Rollenspezifischer Versand von Verleih-Mails (kein CC zwischen Ausleihende*r und MW)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from lamathek.models.loan import Loan
from lamathek.models.user import User
from lamathek.services.inventories import permission_users, user_can_manage_inventory
from lamathek.services.journal import append_journal
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


def enqueue_loan_receipt_mails(
    session: Session,
    loan: Loan,
    action: str,
    line_ids: list[int],
    *,
    actor: User,
    mail_step: str | None = None,
    pdf_kind: str | None = None,
    locale: str = "de",
) -> None:
    """Put the mails for both audiences into the outbox (same transaction as the step).

    The PDF list goes to Materialwart*innen only; Ausleihende open it in the app.
    Without a usable address nothing is queued and the journal says so.
    """
    from lamathek.models.mail import OUTBOX_KIND_LOAN
    from lamathek.services.loan_notifications import mail_delivery_possible
    from lamathek.services.outbox import enqueue

    if not mail_delivery_possible():
        # Installation without SMTP: the workflow runs, the journal says why no mail went out.
        append_journal(
            session,
            "mail.skipped",
            actor,
            {"action": action, "reason": "smtp_not_configured"},
            loan_id=loan.id,
        )
        return
    for audience in _LOAN_MAIL_AUDIENCES:
        recipients = recipients_for_audience(session, loan, audience)
        if recipients is None:
            append_journal(
                session,
                "mail.skipped",
                actor,
                {"action": action, "audience": audience, "reason": "no_address"},
                loan_id=loan.id,
            )
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
        enqueue(
            session,
            kind=OUTBOX_KIND_LOAN,
            to=recipients.to,
            cc=recipients.cc,
            subject=subject,
            text=text,
            html=html,
            loan_id=loan.id,
            audience=audience,
            pdf_kind=pdf_kind if audience == "managers" else None,
        )
