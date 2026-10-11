from flask import Blueprint, jsonify, request

from lamathek.routes.http_errors import error_response
from lamathek.routes.parsing import parse_date
from sqlalchemy import select

from lamathek.access import require_inventory_manager, require_login
from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.serializers import (
    event_to_json,
    group_to_json,
    loan_detail_to_json,
    loan_to_json,
)
from lamathek.services.inventories import user_can_manage_any_inventory, user_can_manage_inventory
from lamathek.services.photos import cover_photo_ids_for_loans
from lamathek.services.loans import (
    add_piece_line,
    add_set_assignment_lines,
    add_set_optional_lines,
    add_stock_line,
    create_loan,
    hand_out_loan,
    list_events,
    list_groups,
    list_loans,
    loan_by_id,
    record_loan_return,
    remove_line,
    update_loan,
)

loans_bp = Blueprint("loans", __name__, url_prefix="/api")


def _loan_status(code: str) -> int:
    status = 400
    if code == "not_found":
        status = 404
    if code in (
        "piece_unavailable",
        "over_loaned",
        "line_exists",
        "loan_not_editable",
        "set_unavailable",
        "empty_loan",
        "loan_not_returnable",
        "line_already_settled",
        "over_returned",
        "set_already_added",
        "piece_on_loan",
    ):
        status = 409
    if code in ("invalid_permanent_fields", "invalid_date_range", "invalid_scope"):
        status = 400
    if code in ("invalid_set", "invalid_piece", "invalid_material_type", "invalid_responsible"):
        status = 400
    return status


def _loan_error(exc: ValueError):
    return error_response(exc, _loan_status)


@loans_bp.get("/groups")
@require_login
def get_groups(_user):
    session = get_session()
    return jsonify([group_to_json(g) for g in list_groups(session)])


@loans_bp.post("/groups")
@require_login
def post_group(_user):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    from lamathek.services.loans import get_or_create_group

    session = get_session()
    group = get_or_create_group(session, name)
    session.commit()
    return jsonify(group_to_json(group)), 201


@loans_bp.get("/events")
@require_login
def get_events(_user):
    session = get_session()
    return jsonify([event_to_json(e) for e in list_events(session)])


@loans_bp.post("/events")
@require_login
def post_event(_user):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    from lamathek.services.loans import get_or_create_event

    session = get_session()
    event = get_or_create_event(session, name)
    session.commit()
    return jsonify(event_to_json(event)), 201


@loans_bp.get("/users/verantwortliche")
@require_login
def get_verantwortliche(user):
    session = get_session()
    if not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    users = session.scalars(select(User).order_by(User.name, User.email)).all()
    from lamathek.serializers import user_to_json

    return jsonify([user_to_json(u) for u in users])


@loans_bp.get("/inventories/<int:inventory_id>/loans")
@require_inventory_manager()
def get_loans(_user, inventory):
    session = get_session()
    loans = list_loans(session, inventory.id)
    covers = cover_photo_ids_for_loans(session, [loan.id for loan in loans])
    return jsonify(
        [loan_to_json(loan, cover_photo_id=covers.get(loan.id)) for loan in loans]
    )


@loans_bp.post("/inventories/<int:inventory_id>/loans")
@require_inventory_manager()
def post_loan(_user, inventory):
    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")
    responsible_user_id = body.get("responsibleUserId")
    if not isinstance(group_name, str) or not group_name.strip():
        return jsonify({"error": "invalid_group"}), 400
    if not isinstance(responsible_user_id, int):
        return jsonify({"error": "invalid_responsible"}), 400
    event_name = body.get("eventName")
    if event_name is not None and not isinstance(event_name, str):
        return jsonify({"error": "invalid_event"}), 400
    loan_kind = body.get("kind", "short")
    if not isinstance(loan_kind, str):
        return jsonify({"error": "invalid_kind"}), 400
    try:
        starts_on = parse_date(body.get("startsOn"))
        ends_on = parse_date(body.get("endsOn"))
    except ValueError:
        return jsonify({"error": "invalid_date"}), 400

    session = get_session()
    try:
        loan = create_loan(
            session,
            inventory,
            group_name=group_name,
            responsible_user_id=responsible_user_id,
            event_name=event_name,
            starts_on=starts_on,
            ends_on=ends_on,
            kind=loan_kind,
        )
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(loan_detail_to_json(loan)), 201


@loans_bp.get("/loans/<int:loan_id>")
@require_login
def get_loan(user, loan_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403
    covers = cover_photo_ids_for_loans(session, [loan.id])
    return jsonify(loan_detail_to_json(loan, cover_photo_id=covers.get(loan.id)))


@loans_bp.patch("/loans/<int:loan_id>")
@require_login
def patch_loan(user, loan_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    kwargs: dict = {}
    if "groupName" in body:
        name = body["groupName"]
        if not isinstance(name, str) or not name.strip():
            return jsonify({"error": "invalid_group"}), 400
        kwargs["group_name"] = name
    if "responsibleUserId" in body:
        if not isinstance(body["responsibleUserId"], int):
            return jsonify({"error": "invalid_responsible"}), 400
        kwargs["responsible_user_id"] = body["responsibleUserId"]
    if body.get("clearEvent") is True:
        kwargs["clear_event"] = True
    elif "eventName" in body:
        event_name = body["eventName"]
        if event_name is not None and not isinstance(event_name, str):
            return jsonify({"error": "invalid_event"}), 400
        kwargs["event_name"] = event_name
    if "startsOn" in body:
        try:
            kwargs["starts_on"] = parse_date(body.get("startsOn"))
            kwargs["update_starts_on"] = True
        except ValueError:
            return jsonify({"error": "invalid_date"}), 400
    if "endsOn" in body:
        try:
            kwargs["ends_on"] = parse_date(body.get("endsOn"))
            kwargs["update_ends_on"] = True
        except ValueError:
            return jsonify({"error": "invalid_date"}), 400
    if "kind" in body:
        kind = body["kind"]
        if not isinstance(kind, str):
            return jsonify({"error": "invalid_kind"}), 400
        kwargs["kind"] = kind

    try:
        loan = update_loan(session, loan, **kwargs)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(loan_detail_to_json(loan))


@loans_bp.post("/loans/<int:loan_id>/lines")
@require_login
def post_loan_line(user, loan_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    session = get_session()
    loan = loan_by_id(session, loan_id)
    try:
        if "setId" in body:
            if not isinstance(body["setId"], int):
                return jsonify({"error": "invalid_set"}), 400
            scope = body.get("scope", "assignment")
            if scope == "optionals":
                add_set_optional_lines(session, loan, body["setId"])
            elif scope == "assignment":
                add_set_assignment_lines(session, loan, body["setId"])
            else:
                return jsonify({"error": "invalid_scope"}), 400
        elif "pieceId" in body:
            if not isinstance(body["pieceId"], int):
                return jsonify({"error": "invalid_piece"}), 400
            add_piece_line(session, loan, body["pieceId"])
        elif "materialTypeId" in body:
            if not isinstance(body["materialTypeId"], int) or not isinstance(
                body.get("quantity"), int
            ):
                return jsonify({"error": "invalid_material_type"}), 400
            add_stock_line(session, loan, body["materialTypeId"], body["quantity"])
        else:
            return jsonify({"error": "invalid_line"}), 400
    except ValueError as exc:
        return _loan_error(exc)
    loan = loan_by_id(session, loan_id)
    return jsonify(loan_detail_to_json(loan)), 201


@loans_bp.delete("/loans/<int:loan_id>/lines/<int:line_id>")
@require_login
def delete_loan_line(user, loan_id: int, line_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403
    try:
        remove_line(session, loan, line_id)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify({"ok": True})


@loans_bp.post("/loans/<int:loan_id>/returns")
@require_login
def post_loan_return(user, loan_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    try:
        recorded_on = parse_date(body.get("recordedOn"))
    except ValueError:
        return jsonify({"error": "invalid_date"}), 400
    if recorded_on is None:
        return jsonify({"error": "invalid_date"}), 400

    entries = body.get("entries")
    if not isinstance(entries, list):
        return jsonify({"error": "invalid_entries"}), 400

    parsed: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return jsonify({"error": "invalid_entries"}), 400
        loan_line_id = entry.get("loanLineId")
        outcome = entry.get("outcome")
        quantity = entry.get("quantity")
        if not isinstance(loan_line_id, int):
            return jsonify({"error": "invalid_entries"}), 400
        if not isinstance(outcome, str):
            return jsonify({"error": "invalid_entries"}), 400
        if quantity is not None and not isinstance(quantity, int):
            return jsonify({"error": "invalid_entries"}), 400
        parsed.append(
            {"loanLineId": loan_line_id, "outcome": outcome, "quantity": quantity}
        )

    try:
        loan = record_loan_return(session, loan, recorded_on, parsed)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(loan_detail_to_json(loan)), 201


@loans_bp.post("/loans/<int:loan_id>/hand-out")
@require_login
def post_hand_out(user, loan_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403
    try:
        loan = hand_out_loan(session, loan)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(loan_detail_to_json(loan))
