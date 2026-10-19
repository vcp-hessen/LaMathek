from flask import Blueprint, Response, jsonify, request

from lamathek.access import require_login
from lamathek.db import get_session
from lamathek.models.calendar import (
    CALENDAR_SCOPE_BORROWER,
    CALENDAR_SCOPE_CONTACT,
    CALENDAR_SCOPE_INVENTORY,
)
from lamathek.services.calendar import (
    assert_inventory_calendar,
    calendar_feed_ics_url,
    calendar_feed_to_json,
    create_calendar_feed,
    delete_calendar_feed,
    feed_by_token,
    feed_matches_ics_route,
    feed_still_permitted,
    ics_for_loans,
    list_calendar_feeds,
    loan_to_calendar_item,
    loans_for_borrower_calendar,
    loans_for_contact_calendar,
    loans_for_feed,
    loans_for_inventory_calendar,
)
from lamathek.services.inventories import inventory_by_id
from lamathek.services.users import user_by_id

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api")

_FEED_SCOPES = frozenset(
    {CALENDAR_SCOPE_BORROWER, CALENDAR_SCOPE_CONTACT, CALENDAR_SCOPE_INVENTORY}
)


def _items(loans, viewer_id: int | None):
    return [loan_to_calendar_item(loan, viewer_id=viewer_id) for loan in loans]


@calendar_bp.get("/me/calendar/borrower")
@require_login
def get_my_calendar_borrower(user):
    session = get_session()
    loans = loans_for_borrower_calendar(session, user)
    return jsonify({"items": _items(loans, user.id)})


@calendar_bp.get("/me/calendar/contact")
@require_login
def get_my_calendar_contact(user):
    session = get_session()
    loans = loans_for_contact_calendar(session, user)
    return jsonify({"items": _items(loans, user.id)})


@calendar_bp.get("/me/calendar-feeds")
@require_login
def get_my_calendar_feeds(user):
    session = get_session()
    feeds = list_calendar_feeds(session, user)
    return jsonify(
        {"items": [calendar_feed_to_json(session, feed) for feed in feeds]}
    )


@calendar_bp.post("/me/calendar-feeds")
@require_login
def post_my_calendar_feed(user):
    body = request.get_json(silent=True) or {}
    label = body.get("label")
    if not isinstance(label, str) or not label.strip():
        return jsonify({"error": "invalid_label"}), 400
    scope = body.get("scope", CALENDAR_SCOPE_BORROWER)
    if scope not in _FEED_SCOPES:
        return jsonify({"error": "invalid_scope"}), 400
    inventory_id = body.get("inventoryId")
    if scope == CALENDAR_SCOPE_BORROWER:
        inventory_id = None
    elif not isinstance(inventory_id, int):
        return jsonify({"error": "invalid_inventory"}), 400

    session = get_session()
    try:
        feed, token = create_calendar_feed(
            session,
            user,
            label=label,
            scope=scope,
            inventory_id=inventory_id,
        )
    except ValueError as exc:
        code = str(exc)
        if code in ("not_found", "forbidden"):
            status = 404 if code == "not_found" else 403
            return jsonify({"error": code}), status
        return jsonify({"error": code}), 400

    payload = calendar_feed_to_json(session, feed)
    payload["token"] = token
    payload["path"] = calendar_feed_ics_url(feed, token)
    return jsonify(payload), 201


@calendar_bp.delete("/me/calendar-feeds/<int:feed_id>")
@require_login
def delete_my_calendar_feed(user, feed_id: int):
    session = get_session()
    if not delete_calendar_feed(session, user, feed_id):
        return jsonify({"error": "not_found"}), 404
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


def _calendar_ics_response(scope: str, inventory_id: int | None):
    token = request.args.get("token")
    if not isinstance(token, str) or not token.strip():
        return jsonify({"error": "not_found"}), 404
    session = get_session()
    feed = feed_by_token(session, token.strip())
    if feed is None or not feed_matches_ics_route(feed, scope, inventory_id):
        return jsonify({"error": "not_found"}), 404
    owner = user_by_id(session, feed.user_id)
    if owner is None or not feed_still_permitted(session, feed, owner):
        return jsonify({"error": "not_found"}), 404
    loans = loans_for_feed(session, feed, owner)
    body = ics_for_loans(loans)
    return Response(body, mimetype="text/calendar")


@calendar_bp.get("/calendar/ics/borrower.ics")
def get_calendar_ics_borrower():
    return _calendar_ics_response(CALENDAR_SCOPE_BORROWER, None)


@calendar_bp.get("/calendar/ics/inventories/<int:inventory_id>/contact.ics")
def get_calendar_ics_contact(inventory_id: int):
    return _calendar_ics_response(CALENDAR_SCOPE_CONTACT, inventory_id)


@calendar_bp.get("/calendar/ics/inventories/<int:inventory_id>/all-loans.ics")
def get_calendar_ics_inventory(inventory_id: int):
    return _calendar_ics_response(CALENDAR_SCOPE_INVENTORY, inventory_id)
