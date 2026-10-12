from flask import Blueprint, jsonify, request

from lamathek.access import require_superuser
from lamathek.services.mail import (
    get_test_job,
    is_valid_email,
    mail_configured,
    mail_status,
    start_test_mail,
    test_job_to_json,
)

mail_bp = Blueprint("mail", __name__, url_prefix="/api/mail")


@mail_bp.get("/status")
@require_superuser
def get_mail_status(_user):
    return jsonify(mail_status())


@mail_bp.post("/test")
@require_superuser
def post_mail_test(user):
    if not mail_configured():
        return jsonify({"error": "smtp_not_configured"}), 400

    body = request.get_json(silent=True) or {}
    to = body.get("to")
    if not isinstance(to, str) or not is_valid_email(to):
        return jsonify({"error": "invalid_recipient"}), 400

    job_id = start_test_mail(user.id, to.strip())
    return jsonify({"id": job_id}), 202


@mail_bp.get("/test/<job_id>")
@require_superuser
def get_mail_test(user, job_id: str):
    job = get_test_job(job_id, user.id)
    if job is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(test_job_to_json(job))
