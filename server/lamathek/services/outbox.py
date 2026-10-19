"""Mail-Outbox: mails are rows written with the change they report, sent later.

A workflow step therefore always completes in one commit, whatever SMTP does.
The worker claims due rows with a short lease (an UPDATE that only one process
can win), so several gunicorn workers or the dev reloader never send twice.
Failed sends are retried with backoff and finally marked ``failed``; Material-
wart*innen see that on the Verleih and can send again.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from flask import Flask
from sqlalchemy import event, or_, select, update
from sqlalchemy.orm import Session

from lamathek.models.mail import (
    OUTBOX_FAILED,
    OUTBOX_KIND_LOAN,
    OUTBOX_PENDING,
    OUTBOX_SENDING,
    OUTBOX_SENT,
    MailOutbox,
)

logger = logging.getLogger(__name__)

# Minutes before attempt 2, 3, …; after the last one the row is ``failed``.
BACKOFF_MINUTES = (1, 5, 30, 120, 360)
LEASE = timedelta(minutes=5)
POLL_SECONDS = 10

_wake = threading.Event()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; compare everything as naive UTC."""
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def enqueue(
    session: Session,
    *,
    kind: str,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
    cc: list[str] | None = None,
    loan_id: int | None = None,
    audience: str | None = None,
    pdf_kind: str | None = None,
    requested_by_user_id: int | None = None,
    max_attempts: int = len(BACKOFF_MINUTES) + 1,
) -> MailOutbox:
    """Add a mail to the caller's transaction; the worker wakes after its commit."""
    row = MailOutbox(
        kind=kind,
        loan_id=loan_id,
        audience=audience,
        requested_by_user_id=requested_by_user_id,
        to_address=to,
        cc=list(cc or []),
        subject=subject,
        text_body=text,
        html_body=html,
        pdf_kind=pdf_kind,
        status=OUTBOX_PENDING,
        attempts=0,
        max_attempts=max_attempts,
        next_attempt_at=_naive_utc(utcnow()),
        last_error="",
    )
    session.add(row)
    event.listen(session, "after_commit", lambda _s: _wake.set(), once=True)
    return row


def _claim(session: Session, now: datetime) -> list[int]:
    now = _naive_utc(now)
    due = session.scalars(
        select(MailOutbox.id)
        .where(
            MailOutbox.status.in_((OUTBOX_PENDING, OUTBOX_SENDING)),
            MailOutbox.next_attempt_at <= now,
            or_(MailOutbox.locked_until.is_(None), MailOutbox.locked_until < now),
        )
        .order_by(MailOutbox.id)
        .limit(20)
    ).all()
    claimed = []
    for row_id in due:
        result = session.execute(
            update(MailOutbox)
            .where(
                MailOutbox.id == row_id,
                or_(MailOutbox.locked_until.is_(None), MailOutbox.locked_until < now),
            )
            .values(status=OUTBOX_SENDING, locked_until=now + LEASE)
        )
        if result.rowcount == 1:
            claimed.append(row_id)
    session.commit()
    return claimed


def _attachments(session: Session, row: MailOutbox):
    if not row.pdf_kind or row.loan_id is None:
        return None
    from lamathek.services.loan_pdf import pdf_filename, render_loan_pdf
    from lamathek.services.loans import loan_by_id

    loan = loan_by_id(session, row.loan_id)
    if loan is None:
        return None
    return [(pdf_filename(loan, row.pdf_kind), render_loan_pdf(session, loan, row.pdf_kind), "application/pdf")]


def _journal(session: Session, row: MailOutbox, kind: str, **extra) -> None:
    if row.kind != OUTBOX_KIND_LOAN or row.loan_id is None:
        return
    from lamathek.services.journal import append_journal

    append_journal(
        session,
        kind,
        None,
        {"audience": row.audience, "pdfKind": row.pdf_kind, "attempt": row.attempts, **extra},
        loan_id=row.loan_id,
    )


def _deliver(session: Session, row: MailOutbox, now: datetime) -> None:
    from lamathek.services.loan_notifications import get_mail_sender

    row.attempts += 1
    try:
        attachments = _attachments(session, row)
        get_mail_sender()(
            row.to_address, row.subject, row.text_body, row.html_body, list(row.cc or []), attachments
        )
    except Exception as exc:  # noqa: BLE001 - any failure is recorded on the row
        detail = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
        row.last_error = detail[:500]
        row.locked_until = None
        if row.attempts >= row.max_attempts:
            row.status = OUTBOX_FAILED
            _journal(session, row, "mail.failed", error=row.last_error)
        else:
            row.status = OUTBOX_PENDING
            wait = BACKOFF_MINUTES[min(row.attempts - 1, len(BACKOFF_MINUTES) - 1)]
            row.next_attempt_at = _naive_utc(now) + timedelta(minutes=wait)
        logger.warning("Mail %s attempt %s failed: %s", row.id, row.attempts, row.last_error)
        return
    row.status = OUTBOX_SENT
    row.sent_at = _naive_utc(now)
    row.locked_until = None
    row.last_error = ""
    _journal(session, row, "mail.sent")


def process_outbox_once(session: Session, now: datetime | None = None) -> int:
    """Send every due mail once; returns how many were attempted."""
    now = now or utcnow()
    claimed = _claim(session, now)
    for row_id in claimed:
        row = session.get(MailOutbox, row_id)
        if row is None:
            continue
        _deliver(session, row, now)
        session.commit()
    return len(claimed)


def resend(session: Session, row: MailOutbox) -> MailOutbox:
    """Queue a failed (or retrying) mail again right away, with fresh attempts."""
    if row.status == OUTBOX_SENT:
        raise ValueError("mail_already_sent")
    row.status = OUTBOX_PENDING
    row.attempts = 0
    row.next_attempt_at = _naive_utc(utcnow())
    row.locked_until = None
    event.listen(session, "after_commit", lambda _s: _wake.set(), once=True)
    return row


def outbox_to_json(row: MailOutbox) -> dict:
    def iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()

    return {
        "id": row.id,
        "kind": row.kind,
        "loanId": row.loan_id,
        "audience": row.audience,
        "to": row.to_address,
        "subject": row.subject,
        "pdfKind": row.pdf_kind,
        "status": row.status,
        "attempts": row.attempts,
        "lastError": row.last_error or None,
        "createdAt": iso(row.created_at),
        "sentAt": iso(row.sent_at),
        "nextAttemptAt": iso(row.next_attempt_at) if row.status == OUTBOX_PENDING else None,
    }


def start_outbox_worker(app: Flask) -> threading.Thread:
    """Daemon thread that sends due mails; woken right after each enqueue commit."""

    def run() -> None:
        from lamathek import db

        while True:
            _wake.clear()
            try:
                with app.app_context():
                    session = db.SessionLocal()
                    try:
                        process_outbox_once(session)
                    finally:
                        session.close()
            except Exception:  # noqa: BLE001 - the worker must survive anything
                logger.exception("Mail outbox worker iteration failed")
            _wake.wait(POLL_SECONDS)

    thread = threading.Thread(target=run, name="mail-outbox", daemon=True)
    thread.start()
    return thread
