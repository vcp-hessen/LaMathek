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
    return jsonify(settings_to_json(settings, session))


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

    def text_field(key: str) -> str:
        value = body.get(key)
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("invalid_field")
        return value

    map_latitude = body.get("mapLatitude")
    map_longitude = body.get("mapLongitude")
    if not isinstance(map_latitude, (int, float)) or not isinstance(
        map_longitude, (int, float)
    ):
        return jsonify({"error": "invalid_map_center"}), 400

    try:
        session = get_session()
        settings = update_installation_settings(
            session,
            title=title,
            subtitle=subtitle,
            legal_name=text_field("legalName"),
            legal_address=text_field("legalAddress"),
            email=text_field("email"),
            website=text_field("website"),
            phone=text_field("phone"),
            represented_by=text_field("representedBy"),
            register=text_field("register"),
            map_latitude=float(map_latitude),
            map_longitude=float(map_longitude),
        )
    except ValueError:
        return jsonify({"error": "invalid_field"}), 400
    return jsonify(settings_to_json(settings, session))
