import email.utils
import logging
import re
import smtplib
from email.message import EmailMessage
from typing import Literal

from flask import current_app, has_app_context

from lamathek.config import Config
from lamathek.db import get_session
from lamathek.services.settings import get_installation_settings

logger = logging.getLogger(__name__)


def _cfg(name: str, default=None):
    if has_app_context():
        return current_app.config.get(name, default)
    return getattr(Config, name, default)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_valid_email(address: str) -> bool:
    return bool(_EMAIL_RE.match(address.strip()))


def mail_configured() -> bool:
    host = str(_cfg("SMTP_HOST", "") or "").strip()
    from_addr = str(_cfg("SMTP_FROM", "") or "").strip()
    return bool(host and from_addr)


def _transport_mode() -> Literal["ssl", "starttls", "plain"]:
    if _cfg("SMTP_SSL", False):
        return "ssl"
    if _cfg("SMTP_STARTTLS", True):
        return "starttls"
    return "plain"


def mail_status() -> dict:
    mode = _transport_mode()
    configured = mail_configured()
    host = str(_cfg("SMTP_HOST", "") or "").strip()
    from_addr = str(_cfg("SMTP_FROM", "") or "").strip()
    return {
        "configured": configured,
        "host": host if configured else "",
        "port": int(_cfg("SMTP_PORT", 587)) if configured else 0,
        "fromAddress": from_addr if configured else "",
        "mode": mode if configured else "",
        "hasCredentials": bool(str(_cfg("SMTP_USERNAME", "") or "").strip()),
    }


class MailDeliveryError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def _smtp_from_header() -> str:
    raw = str(_cfg("SMTP_FROM", "") or "").strip()
    if not raw:
        return ""
    _name, addr = email.utils.parseaddr(raw)
    if not addr:
        return raw
    session = get_session()
    settings = get_installation_settings(session)
    title = (settings.title or "").strip()
    if title:
        return email.utils.formataddr((title, addr))
    if _name:
        return email.utils.formataddr((_name, addr))
    return addr


def send_mail(
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
    *,
    cc: list[str] | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> None:
    if not mail_configured():
        raise MailDeliveryError("smtp_not_configured")

    message = EmailMessage()
    message["From"] = _smtp_from_header()
    message["To"] = to
    if cc:
        filtered = [addr.strip() for addr in cc if addr.strip() and addr.strip() != to]
        if filtered:
            message["Cc"] = ", ".join(filtered)
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")
    if attachments:
        for filename, data, mime in attachments:
            maintype, _, subtype = mime.partition("/")
            if not subtype:
                maintype, subtype = "application", "octet-stream"
            message.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )

    timeout = float(_cfg("SMTP_TIMEOUT", 15))
    host = str(_cfg("SMTP_HOST", "") or "").strip()
    port = int(_cfg("SMTP_PORT", 587))
    username = str(_cfg("SMTP_USERNAME", "") or "").strip()
    password = _cfg("SMTP_PASSWORD", "") or ""
    use_ssl = bool(_cfg("SMTP_SSL", False))
    use_starttls = bool(_cfg("SMTP_STARTTLS", True))

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                if use_starttls:
                    smtp.starttls()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
    except smtplib.SMTPException as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        logger.warning("SMTP delivery failed to %s: %s", to, detail)
        raise MailDeliveryError(detail) from exc
    except OSError as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        logger.warning("SMTP connection failed to %s:%s: %s", host, port, detail)
        raise MailDeliveryError(detail) from exc


def start_test_mail(session, owner_user_id: int, to: str) -> int:
    """Queue a test mail through the outbox (one attempt, the result shows the error)."""
    from lamathek.models.mail import OUTBOX_KIND_TEST
    from lamathek.services.mail_templates import render_mail
    from lamathek.services.outbox import enqueue

    subject, text, html = render_mail(
        "test",
        heading="Testmail",
        paragraphs=[
            "Dies ist eine Testnachricht von LaMathek.",
            "Wenn Sie diese E-Mail erhalten, ist der SMTP-Versand korrekt konfiguriert.",
        ],
    )
    row = enqueue(
        session,
        kind=OUTBOX_KIND_TEST,
        to=to,
        subject=subject,
        text=text,
        html=html,
        requested_by_user_id=owner_user_id,
        max_attempts=1,
    )
    session.commit()
    return row.id


def test_mail_status(session, row_id: int, owner_user_id: int) -> dict | None:
    from lamathek.models.mail import OUTBOX_FAILED, OUTBOX_SENT, MailOutbox

    row = session.get(MailOutbox, row_id)
    if row is None or row.kind != "test" or row.requested_by_user_id != owner_user_id:
        return None
    if row.status == OUTBOX_SENT:
        return {"status": "sent", "detail": None}
    if row.status == OUTBOX_FAILED:
        return {"status": "failed", "detail": row.last_error}
    return {"status": "pending", "detail": None}
