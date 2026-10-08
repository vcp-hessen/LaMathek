from flask import Blueprint, jsonify, request

from lamathek.access import require_superuser
from lamathek.db import get_session
from lamathek.serializers import settings_to_json
from lamathek.services.settings import get_installation_settings, update_installation_settings

settings_bp = Blueprint("settings", __name__, url_prefix="/api")


@settings_bp.get("/settings")
def get_settings():
    session = get_session()
    settings = get_installation_settings(session)
    return jsonify(settings_to_json(settings))


@settings_bp.patch("/settings")
@require_superuser
def patch_settings(_user):
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    subtitle = body.get("subtitle")
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "invalid_title"}), 400
    if not isinstance(subtitle, str) or not subtitle.strip():
        return jsonify({"error": "invalid_subtitle"}), 400
    session = get_session()
    settings = update_installation_settings(
        session, title=title, subtitle=subtitle
    )
    return jsonify(settings_to_json(settings))
