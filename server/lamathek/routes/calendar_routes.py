from flask import Blueprint, Response, jsonify, request

from lamathek.access import require_login
from lamathek.db import get_session
from lamathek.models.calendar import CALENDAR_SCOPE_INVENTORY, CALENDAR_SCOPE_USER
from lamathek.services.calendar import (
    assert_inventory_calendar,
    feed_by_token,
    ics_for_loans,
    issue_feed_token,
    loan_to_calendar_item,
    loans_for_inventory_calendar,
    loans_for_user_calendar,
    revoke_feed,
)
from lamathek.services.inventories import inventory_by_id
from lamathek.services.users import user_by_id

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api")


def _items(loans, viewer_id: int | None):
    return [loan_to_calendar_item(loan, viewer_id=viewer_id) for loan in loans]


@calendar_bp.get("/me/calendar")
@require_login
def get_my_calendar(user):
    session = get_session()
    loans = loans_for_user_calendar(session, user)
    return jsonify({"items": _items(loans, user.id)})


@calendar_bp.post("/me/calendar-token")
@require_login
def post_my_calendar_token(user):
    session = get_session()
    token = issue_feed_token(session, user, scope=CALENDAR_SCOPE_USER)
    return jsonify({"token": token, "path": f"/api/calendar/{token}.ics"}), 201


@calendar_bp.delete("/me/calendar-token")
@require_login
def delete_my_calendar_token(user):
    revoke_feed(get_session(), user, scope=CALENDAR_SCOPE_USER)
    return "", 204


@calendar_bp.get("/inventories/<int:inventory_id>/calendar")
@require_login
def get_inventory_calendar(user, inventory_id: int):
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    try:
        assert_inventory_calendar(session, user, inventory)
    except ValueError:
        return jsonify({"error": "forbidden"}), 403
    loans = loans_for_inventory_calendar(session, inventory_id)
    return jsonify({"items": _items(loans, user.id)})


@calendar_bp.post("/inventories/<int:inventory_id>/calendar-token")
@require_login
def post_inventory_calendar_token(user, inventory_id: int):
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    try:
        assert_inventory_calendar(session, user, inventory)
    except ValueError:
        return jsonify({"error": "forbidden"}), 403
    token = issue_feed_token(
        session, user, scope=CALENDAR_SCOPE_INVENTORY, inventory_id=inventory_id
    )
    return jsonify({"token": token, "path": f"/api/calendar/{token}.ics"}), 201


@calendar_bp.get("/calendar/<token>.ics")
def get_calendar_ics(token: str):
    session = get_session()
    feed = feed_by_token(session, token)
    if feed is None:
        return jsonify({"error": "not_found"}), 404
    owner = user_by_id(session, feed.user_id)
    if owner is None:
        return jsonify({"error": "not_found"}), 404
    if feed.scope == CALENDAR_SCOPE_INVENTORY and feed.inventory_id is not None:
        loans = loans_for_inventory_calendar(session, feed.inventory_id)
    else:
        loans = loans_for_user_calendar(session, owner)
    body = ics_for_loans(loans)
    return Response(body, mimetype="text/calendar")
