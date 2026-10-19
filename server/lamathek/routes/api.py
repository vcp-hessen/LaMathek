from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from lamathek import db
from lamathek.access import require_login
from lamathek.auth import dev_bypass_enabled, session_actor_sub, session_impersonation
from lamathek.db import get_session
from lamathek.serializers import user_to_json
from lamathek.services.users import update_user_phone, user_by_oidc_sub

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health():
    with db.engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return jsonify({"status": "ok"})


@api_bp.get("/auth/mode")
def auth_mode():
    return jsonify({"devBypass": dev_bypass_enabled(current_app)})


@api_bp.get("/me")
@require_login
def me(user):
    body = user_to_json(user, include_sub=True)
    imp = session_impersonation()
    if imp is None:
        body["impersonation"] = None
    else:
        db = get_session()
        actor_sub = session_actor_sub()
        actor = user_by_oidc_sub(db, actor_sub) if actor_sub else None
        body["impersonation"] = {
            "actor": user_to_json(actor, include_sub=True) if actor is not None else None,
            "reason": imp.get("reason"),
            "startedAt": imp.get("startedAt"),
        }
    return jsonify(body)


@api_bp.patch("/me")
@require_login
def patch_me(user):
    body = request.get_json(silent=True) or {}
    if "phone" in body:
        phone = body.get("phone")
        if not isinstance(phone, str):
            return jsonify({"error": "invalid_phone"}), 400
        session = get_session()
        user = update_user_phone(session, user, phone)
    return jsonify(user_to_json(user))
