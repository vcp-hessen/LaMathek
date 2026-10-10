from flask import Blueprint, jsonify, request

from lamathek.access import require_login
from lamathek.db import get_session
from lamathek.services.geocoding import GeocodingError, geocode_address
from lamathek.services.inventories import user_can_manage_any_inventory

geocode_bp = Blueprint("geocode", __name__, url_prefix="/api")


@geocode_bp.get("/geocode")
@require_login
def get_geocode(user):
    session = get_session()
    if not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    query = request.args.get("q", "")
    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "invalid_query"}), 400
    try:
        latitude, longitude = geocode_address(query)
    except GeocodingError as exc:
        code = str(exc)
        if code == "not_found":
            return jsonify({"error": "not_found"}), 404
        return jsonify({"error": code}), 400
    return jsonify({"latitude": latitude, "longitude": longitude})
