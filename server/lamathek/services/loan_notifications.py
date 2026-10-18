from typing import Callable

from sqlalchemy.orm import Session

from lamathek.models.loan import Loan
from lamathek.models.user import User
from lamathek.services.loan_mail_dispatch import dispatch_loan_mail
from lamathek.services.mail import send_mail

MailSender = Callable[
    [str, str, str, str | None, list[str], list[tuple[str, bytes, str]] | None],
    None,
]

_last_mail: dict | None = None


def get_last_mail_for_tests() -> dict | None:
    return _last_mail


def _default_sender(
    to: str,
    subject: str,
    text: str,
    html: str | None,
    cc: list[str],
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> None:
    global _last_mail
    _last_mail = {
        "to": to,
        "subject": subject,
        "text": text,
        "html": html,
        "cc": cc,
        "attachments": attachments,
    }
    send_mail(to, subject, text, html=html, cc=cc, attachments=attachments)


_mail_sender: MailSender = _default_sender


def get_mail_sender() -> MailSender:
    return _mail_sender


def set_mail_sender_for_tests(sender: MailSender | None) -> None:
    global _mail_sender
    _mail_sender = sender or _default_sender


def notify_loan_action(
    session: Session,
    loan: Loan,
    action: str,
    *,
    actor: User,
    line_ids: list[int],
    mail_step: str | None = None,
) -> None:
    dispatch_loan_mail(
        session,
        loan,
        action,
        line_ids,
        actor=actor,
        mail_step=mail_step,
        locale="de",
    )
