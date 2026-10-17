import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from lamathek.models.inventory import InventoryPermission
from lamathek.models.loan import Loan
from lamathek.models.user import User
from lamathek.services.inventories import permission_users
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.mail import is_valid_email, send_mail
from lamathek.services.mail_templates import render_loan_action_mail

logger = logging.getLogger(__name__)

MailSender = Callable[[str, str, str, str | None, list[str]], None]

_last_mail: dict | None = None


def get_last_mail_for_tests() -> dict | None:
    return _last_mail


def _default_sender(
    to: str,
    subject: str,
    text: str,
    html: str | None,
    cc: list[str],
) -> None:
    global _last_mail
    _last_mail = {"to": to, "subject": subject, "text": text, "html": html, "cc": cc}
    try:
        send_mail(to, subject, text, html=html, cc=cc)
    except Exception as exc:
        logger.warning("Loan mail not sent: %s", exc)


_mail_sender: MailSender = _default_sender


def set_mail_sender_for_tests(sender: MailSender | None) -> None:
    global _mail_sender
    _mail_sender = sender or _default_sender


def _manager_emails(session: Session, inventory_id: int) -> list[str]:
    from lamathek.services.inventories import inventory_by_id

    inventory = inventory_by_id(session, inventory_id)
    users = permission_users(session, inventory.id) if inventory else []
    return [
        u.email.strip()
        for u in users
        if u.email and is_valid_email(u.email)
    ]


def _borrower_email(loan: Loan) -> str | None:
    email = (loan.borrower_user.email or "").strip()
    if email and is_valid_email(email):
        return email
    return None


def _contact_email(loan: Loan) -> str | None:
    if loan.contact_user is None:
        return None
    email = (loan.contact_user.email or "").strip()
    if email and is_valid_email(email):
        return email
    return None


def notify_loan_action(
    session: Session,
    loan: Loan,
    action: str,
    *,
    actor: User,
    line_ids: list[int],
) -> None:
    managers = _manager_emails(session, loan.inventory_id)
    borrower_to = _borrower_email(loan)
    contact_to = _contact_email(loan)
    actor_is_manager = user_can_manage_inventory(session, actor, loan.inventory)

    subject, text, html = render_loan_action_mail(session, loan, action, line_ids)

    if action == "request":
        for addr in managers:
            _mail_sender(addr, subject, text, html, [])
        if borrower_to:
            _mail_sender(borrower_to, subject, text, html, [])
        return

    if actor_is_manager:
        if borrower_to:
            _mail_sender(borrower_to, subject, text, html, [])
        return

    cc = [e for e in managers if e != contact_to]
    to = contact_to or (managers[0] if managers else None)
    if to:
        _mail_sender(to, subject, text, html, cc)
