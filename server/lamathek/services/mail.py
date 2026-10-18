import email.utils
import logging
import re
import smtplib
import threading
import uuid
from dataclasses import dataclass
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

JobStatus = Literal["pending", "sent", "failed"]


@dataclass
class MailTestJob:
    owner_user_id: int
    status: JobStatus = "pending"
    detail: str = ""


_jobs: dict[str, MailTestJob] = {}
_jobs_lock = threading.Lock()


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


def _run_send(
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
    job_id: str | None = None,
) -> None:
    try:
        send_mail(to, subject, text, html)
    except MailDeliveryError as exc:
        if job_id is not None:
            with _jobs_lock:
                job = _jobs.get(job_id)
                if job is not None:
                    job.status = "failed"
                    job.detail = exc.detail
        return

    if job_id is not None:
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is not None:
                job.status = "sent"


def enqueue_mail(
    to: str,
    template: str,
    job_id: str | None = None,
    **context,
) -> None:
    if not is_valid_email(to):
        logger.warning("Skipping mail to invalid address")
        if job_id is not None:
            with _jobs_lock:
                job = _jobs.get(job_id)
                if job is not None:
                    job.status = "failed"
                    job.detail = "invalid_recipient"
        return

    if not mail_configured():
        logger.info("SMTP not configured; skipping mail to %s", to)
        if job_id is not None:
            with _jobs_lock:
                job = _jobs.get(job_id)
                if job is not None:
                    job.status = "failed"
                    job.detail = "smtp_not_configured"
        return

    app = current_app._get_current_object()

    def worker() -> None:
        from lamathek.services.mail_templates import render_mail

        with app.app_context():
            subject, text, html = render_mail(template, **context)
            _run_send(to, subject, text, html, job_id)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def start_test_mail(owner_user_id: int, to: str) -> str:
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = MailTestJob(owner_user_id=owner_user_id)

    enqueue_mail(
        to,
        "test",
        job_id=job_id,
        heading="Testmail",
        paragraphs=[
            "Dies ist eine Testnachricht von LaMathek.",
            (
                "Wenn Sie diese E-Mail erhalten, ist der SMTP-Versand "
                "korrekt konfiguriert."
            ),
        ],
    )
    return job_id


def get_test_job(job_id: str, owner_user_id: int) -> MailTestJob | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None or job.owner_user_id != owner_user_id:
        return None
    return job


def test_job_to_json(job: MailTestJob) -> dict:
    payload: dict = {"status": job.status}
    if job.status == "failed" and job.detail:
        payload["detail"] = job.detail
    return payload
