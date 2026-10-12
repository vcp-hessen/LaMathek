from flask import Blueprint, jsonify, request

from lamathek.access import require_superuser
from lamathek.db import get_session
from lamathek.serializers import settings_to_json
from lamathek.services.audit import (
    installation_settings_audit_values,
    log_installation_settings_update,
)
from lamathek.services.settings import get_installation_settings, update_installation_settings

settings_bp = Blueprint("settings", __name__, url_prefix="/api")


@settings_bp.get("/settings")
def get_settings():
    session = get_session()
    settings = get_installation_settings(session)
    return jsonify(settings_to_json(settings, session))


@settings_bp.patch("/settings")
@require_superuser
def patch_settings(user):
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

    same_host = body.get("authProviderSameHost")
    if same_host is None:
        auth_provider_same_host = False
    elif not isinstance(same_host, bool):
        return jsonify({"error": "invalid_field"}), 400
    else:
        auth_provider_same_host = same_host

    try:
        session = get_session()
        before_values = installation_settings_audit_values(get_installation_settings(session))
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
            host_name=text_field("hostName"),
            host_address=text_field("hostAddress"),
            host_privacy_url=text_field("hostPrivacyUrl"),
            auth_provider_name=text_field("authProviderName"),
            auth_provider_same_host=auth_provider_same_host,
            authority_name=text_field("authorityName"),
            authority_url=text_field("authorityUrl"),
        )
    except ValueError:
        return jsonify({"error": "invalid_field"}), 400
    log_installation_settings_update(
        session, actor=user, before_values=before_values, after=settings
    )
    return jsonify(settings_to_json(settings, session))
