from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from lamathek import db
from lamathek.access import require_login
from lamathek.auth import dev_bypass_enabled
from lamathek.serializers import user_to_json

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
    return jsonify(user_to_json(user))
