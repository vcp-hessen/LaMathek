from flask import Blueprint, jsonify, request

from lamathek.contract import models as api, responds
from lamathek.access import require_superuser
from lamathek.db import get_session
from lamathek.services.mail import (
    is_valid_email,
    mail_configured,
    mail_status,
    start_test_mail,
    test_mail_status,
)

mail_bp = Blueprint("mail", __name__, url_prefix="/api/mail")


@mail_bp.get("/status")
@responds(api.MailStatus)
@require_superuser
def get_mail_status(_user):
    return jsonify(mail_status())


@mail_bp.post("/test")
@responds(api.MailTestStarted, status=202)
@require_superuser
def post_mail_test(user):
    if not mail_configured():
        return jsonify({"error": "smtp_not_configured"}), 400

    body = request.get_json(silent=True) or {}
    to = body.get("to")
    if not isinstance(to, str) or not is_valid_email(to):
        return jsonify({"error": "invalid_recipient"}), 400

    row_id = start_test_mail(get_session(), user.id, to.strip())
    return jsonify({"id": str(row_id)}), 202


@mail_bp.get("/test/<int:job_id>")
@responds(api.MailTestJob)
@require_superuser
def get_mail_test(user, job_id: int):
    status = test_mail_status(get_session(), job_id, user.id)
    if status is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(status)


@mail_bp.get("/outbox")
@responds(list[api.OutboxMail])
@require_superuser
def get_failed_outbox(_user):
    """Mails that gave up after all retries (Diagnose)."""
    from sqlalchemy import select

    from lamathek.models.mail import OUTBOX_FAILED, MailOutbox
    from lamathek.services.outbox import outbox_to_json

    rows = get_session().scalars(
        select(MailOutbox)
        .where(MailOutbox.status == OUTBOX_FAILED)
        .order_by(MailOutbox.id.desc())
        .limit(100)
    ).all()
    return jsonify([outbox_to_json(row) for row in rows])
