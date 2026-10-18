from flask import Blueprint, jsonify

from lamathek.access import require_login
from lamathek.db import get_session
from lamathek.services.dashboard import build_dashboard

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")


@dashboard_bp.get("/dashboard")
@require_login
def get_dashboard(user):
    return jsonify(build_dashboard(get_session(), user))
