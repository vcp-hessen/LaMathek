from flask import Blueprint, jsonify, request

from lamathek.db import get_session
from lamathek.services.impersonation import (
    ImpersonationError,
    actor_user_from_session,
    start_impersonation,
    stop_impersonation,
)

impersonation_bp = Blueprint("impersonation", __name__, url_prefix="/api")


def _impersonation_error_response(exc: ImpersonationError):
    code = exc.code
    if code == "forbidden":
        status = 403
    elif code == "invalid_target":
        status = 404
    else:
        status = 400
    return jsonify({"error": code}), status


@impersonation_bp.post("/impersonation")
def post_impersonation():
    actor = actor_user_from_session(get_session())
    if actor is None:
        return jsonify({"error": "unauthorized"}), 401
    if not actor.is_superuser:
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    user_id = body.get("userId")
    reason = body.get("reason")
    if not isinstance(user_id, int):
        return jsonify({"error": "invalid_target"}), 400
    if not isinstance(reason, str):
        return jsonify({"error": "invalid_reason"}), 400

    session_db = get_session()
    try:
        start_impersonation(
            session_db, actor=actor, target_user_id=user_id, reason=reason
        )
    except ImpersonationError as exc:
        return _impersonation_error_response(exc)

    return "", 204


@impersonation_bp.delete("/impersonation")
def delete_impersonation():
    actor = actor_user_from_session(get_session())
    if actor is None:
        return jsonify({"error": "unauthorized"}), 401
    if not actor.is_superuser:
        return jsonify({"error": "forbidden"}), 403

    session_db = get_session()
    try:
        stop_impersonation(session_db, actor=actor)
    except ImpersonationError as exc:
        return _impersonation_error_response(exc)

    return "", 204
