from flask import Blueprint, jsonify

from lamathek.contract import models as api, responds
from lamathek.access import require_superuser
from lamathek.db import get_session
from lamathek.serializers import audit_event_to_json
from lamathek.services.audit import list_audit_events

audit_bp = Blueprint("audit", __name__, url_prefix="/api")


@audit_bp.get("/audit-events")
@responds(list[api.AuditEvent])
@require_superuser
def get_audit_events(_user):
    session = get_session()
    events = list_audit_events(session)
    return jsonify([audit_event_to_json(e, session) for e in events])
