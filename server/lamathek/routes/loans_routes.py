from flask import Blueprint, jsonify, request

from lamathek.models.loan import LINE_STATUS_DRAFT, is_workflow_loan_phase
from lamathek.services.mail_templates import preview_loan_action_mail

from lamathek.access import require_login
from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.routes.http_errors import error_response
from lamathek.routes.parsing import parse_date
from lamathek.serializers import (
    event_to_json,
    group_to_json,
    loan_detail_to_json,
    loan_to_json,
    user_to_json,
)
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.loan_access import (
    user_can_create_loan_on_inventory,
    user_can_view_loan,
)
from lamathek.services.loan_workflow import (
    cancel_unpacked_loan,
    complete_loan_step,
    confirm_lines,
    decline_lines,
    hand_draft_to_borrower,
    delete_unreleased_loan,
    mark_not_packed,
    mark_not_picked_up,
    notify_added_lines,
    pack_lines,
    pickup_lines,
    record_loss_lines,
    replace_line,
    report_return_lines,
    restock_lines,
    skip_pickup_to_return,
    submit_loan_request,
    undo_pickup_lines,
    unpack_lines,
    withdraw_lines,
)
from lamathek.services.loan_line_restore import restore_loan_line as reopen_loan_line
from lamathek.services.loans import (
    add_piece_line,
    add_set_assignment_lines,
    add_set_optional_lines,
    add_stock_line,
    create_loan,
    get_draft_loan,
    get_or_create_draft_loan,
    list_events,
    list_groups,
    list_loans_for_borrower,
    list_loans_for_manager,
    list_loans_for_user_as_borrower,
    loan_by_id,
    remove_line,
    update_loan,
)
from lamathek.services.photos import cover_photo_ids_for_loans
from sqlalchemy import select

loans_bp = Blueprint("loans", __name__, url_prefix="/api")


def _loan_status(code: str) -> int:
    status = 400
    if code == "not_found":
        status = 404
    if code == "forbidden":
        status = 403
    if code in (
        "piece_unavailable",
        "over_loaned",
        "line_exists",
        "loan_not_editable",
        "set_unavailable",
        "empty_loan",
        "set_already_added",
        "piece_on_loan",
        "draft_exists",
        "invalid_line_status",
        "invalid_loan_state",
        "borrower_phone_required",
        "empty_notify",
        "step_incomplete",
        "workflow_step_mismatch",
        "replacement_blocks_reopen",
        "mail_not_sent",
    ):
        status = 409
    if code in ("invalid_permanent_fields", "invalid_date_range", "invalid_scope"):
        status = 400
    if code in ("invalid_set", "invalid_piece", "invalid_material_type", "invalid_borrower"):
        status = 400
    return status


def _loan_error(exc: ValueError):
    return error_response(exc, _loan_status)


def _require_loan_access(session, user, loan_id: int):
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return None, (jsonify({"error": "not_found"}), 404)
    if not user_can_view_loan(session, user, loan):
        return None, (jsonify({"error": "forbidden"}), 403)
    return loan, None


def _line_ids_from_body(body: dict) -> list[int]:
    raw = body.get("lineIds")
    if not isinstance(raw, list) or not raw:
        raise ValueError("invalid_line_ids")
    ids: list[int] = []
    for item in raw:
        if not isinstance(item, int):
            raise ValueError("invalid_line_ids")
        ids.append(item)
    return ids


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


@loans_bp.get("/users/borrowers")
@require_login
def get_borrowers(user):
    from lamathek.services.inventories import user_can_manage_any_inventory

    session = get_session()
    if not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    users = session.scalars(select(User).order_by(User.name, User.email)).all()
    return jsonify([user_to_json(u) for u in users])


@loans_bp.get("/me/loans")
@require_login
def get_my_loans(user):
    session = get_session()
    loans = list_loans_for_user_as_borrower(session, user)
    covers = cover_photo_ids_for_loans(session, [loan.id for loan in loans])
    return jsonify(
        [
            loan_to_json(loan, cover_photo_id=covers.get(loan.id), viewer=user, session=session)
            for loan in loans
        ]
    )


@loans_bp.get("/inventories/<int:inventory_id>/loans")
@require_login
def get_loans(user, inventory_id: int):
    from lamathek.services.inventories import inventory_by_id, user_can_view_inventory

    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    if user_can_manage_inventory(session, user, inventory):
        loans = list_loans_for_manager(
            session, inventory.id, viewer_user_id=user.id
        )
    elif user_can_view_inventory(session, user, inventory):
        loans = list_loans_for_borrower(session, inventory.id, user.id)
    else:
        return jsonify({"error": "forbidden"}), 403
    covers = cover_photo_ids_for_loans(session, [loan.id for loan in loans])
    return jsonify(
        [
            loan_to_json(loan, cover_photo_id=covers.get(loan.id), viewer=user, session=session)
            for loan in loans
        ]
    )


@loans_bp.get("/inventories/<int:inventory_id>/loans/draft")
@require_login
def get_draft(user, inventory_id: int):
    from lamathek.services.inventories import inventory_by_id

    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_create_loan_on_inventory(session, user, inventory):
        return jsonify({"error": "forbidden"}), 403
    borrower_id = user.id
    body_borrower = request.args.get("borrowerUserId")
    if body_borrower is not None:
        if int(body_borrower) != user.id:
            return jsonify({"error": "forbidden"}), 403
        borrower_id = int(body_borrower)
    draft = get_draft_loan(session, inventory.id, borrower_id)
    if draft is None:
        return jsonify(None)
    covers = cover_photo_ids_for_loans(session, [draft.id])
    return jsonify(
        loan_detail_to_json(
            draft, cover_photo_id=covers.get(draft.id), viewer=user, session=session
        )
    )


@loans_bp.post("/inventories/<int:inventory_id>/loans")
@require_login
def post_loan(user, inventory_id: int):
    from lamathek.services.inventories import inventory_by_id

    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_create_loan_on_inventory(session, user, inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")
    borrower_user_id = body.get("borrowerUserId", user.id)
    if not isinstance(group_name, str) or not group_name.strip():
        return jsonify({"error": "invalid_group"}), 400
    if not isinstance(borrower_user_id, int):
        return jsonify({"error": "invalid_borrower"}), 400
    if borrower_user_id != user.id and not user_can_manage_inventory(
        session, user, inventory
    ):
        return jsonify({"error": "forbidden"}), 403
    event_name = body.get("eventName")
    if event_name is not None and not isinstance(event_name, str):
        return jsonify({"error": "invalid_event"}), 400
    loan_kind = body.get("kind", "short")
    if not isinstance(loan_kind, str):
        return jsonify({"error": "invalid_kind"}), 400
    try:
        pickup_on = parse_date(body.get("pickupOn"))
        return_on = parse_date(body.get("returnOn"))
    except ValueError:
        return jsonify({"error": "invalid_date"}), 400

    try:
        loan = create_loan(
            session,
            inventory,
            group_name=group_name,
            borrower_user_id=borrower_user_id,
            event_name=event_name,
            pickup_on=pickup_on,
            return_on=return_on,
            kind=loan_kind,
            actor=user,
        )
    except ValueError as exc:
        return _loan_error(exc)
    covers = cover_photo_ids_for_loans(session, [loan.id])
    return (
        jsonify(
            loan_detail_to_json(
                loan, cover_photo_id=covers.get(loan.id), viewer=user, session=session
            )
        ),
        201,
    )


@loans_bp.post("/inventories/<int:inventory_id>/loans/draft-lines")
@require_login
def post_draft_line(user, inventory_id: int):
    from lamathek.services.inventories import inventory_by_id

    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_create_loan_on_inventory(session, user, inventory):
        return jsonify({"error": "forbidden"}), 403
    body = request.get_json(silent=True) or {}
    borrower_user_id = body.get("borrowerUserId", user.id)
    if not isinstance(borrower_user_id, int):
        return jsonify({"error": "invalid_borrower"}), 400
    if borrower_user_id != user.id:
        return jsonify({"error": "forbidden"}), 403
    group_name = body.get("groupName") or "—"
    if not isinstance(group_name, str):
        return jsonify({"error": "invalid_group"}), 400
    loan = get_or_create_draft_loan(
        session, inventory, borrower_user_id, group_name=group_name
    )
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
    loan = loan_by_id(session, loan.id)
    covers = cover_photo_ids_for_loans(session, [loan.id])
    return jsonify(
        loan_detail_to_json(
            loan, cover_photo_id=covers.get(loan.id), viewer=user, session=session
        )
    ), 201


@loans_bp.delete("/loans/<int:loan_id>")
@require_login
def delete_loan(user, loan_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    try:
        delete_unreleased_loan(session, loan, actor=user)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify({"ok": True})


@loans_bp.get("/loans/<int:loan_id>/mail-preview")
@require_login
def loan_mail_preview(user, loan_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    if not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403
    action = request.args.get("action", "request")
    if not isinstance(action, str) or not action.strip():
        return jsonify({"error": "invalid_action"}), 400
    audience = request.args.get("audience", "borrower")
    if audience not in ("borrower", "managers"):
        return jsonify({"error": "invalid_audience"}), 400
    variant = request.args.get("variant", "")
    if variant is not None and not isinstance(variant, str):
        return jsonify({"error": "invalid_variant"}), 400
    mail_step = request.args.get("mailStep")
    if mail_step is not None and not isinstance(mail_step, str):
        return jsonify({"error": "invalid_mail_step"}), 400
    if mail_step == "":
        mail_step = None
    if mail_step is None and is_workflow_loan_phase(loan.phase):
        mail_step = loan.phase
    line_ids = [line.id for line in loan.lines if line.status != LINE_STATUS_DRAFT]
    payload = preview_loan_action_mail(
        session,
        loan,
        action.strip(),
        line_ids,
        actor=user,
        audience=audience,
        variant=variant.strip(),
        mail_step=mail_step,
    )
    return jsonify(payload)


@loans_bp.get("/loans/<int:loan_id>")
@require_login
def get_loan(user, loan_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    covers = cover_photo_ids_for_loans(session, [loan.id])
    return jsonify(
        loan_detail_to_json(
            loan, cover_photo_id=covers.get(loan.id), viewer=user, session=session
        )
    )


@loans_bp.patch("/loans/<int:loan_id>")
@require_login
def patch_loan(user, loan_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    is_inventory_manager = user_can_manage_inventory(session, user, loan.inventory)
    is_borrower = user.id == loan.borrower_user_id
    manager_powers = is_inventory_manager and loan.phase != "draft"
    manager_draft_for_other = (
        is_inventory_manager
        and loan.phase == "draft"
        and loan.contact_user_id == user.id
    )
    can_edit_shared = is_borrower or manager_powers or manager_draft_for_other
    body = request.get_json(silent=True) or {}
    kwargs: dict = {}

    def can_edit_draft_meta() -> bool:
        return (
            (loan.phase == "draft" and is_borrower)
            or manager_powers
            or manager_draft_for_other
        )

    def mark_manager_edit() -> None:
        if manager_powers or manager_draft_for_other:
            kwargs["manager_edit"] = True

    if can_edit_shared:
        kwargs["allow_shared_meta"] = True
    if "groupName" in body:
        name = body["groupName"]
        if not isinstance(name, str) or not name.strip():
            return jsonify({"error": "invalid_group"}), 400
        if not can_edit_draft_meta():
            return jsonify({"error": "invalid_loan_state"}), 409
        kwargs["group_name"] = name
        mark_manager_edit()
    if "borrowerUserId" in body:
        borrower_user_id = body["borrowerUserId"]
        if not isinstance(borrower_user_id, int):
            return jsonify({"error": "invalid_borrower"}), 400
        if not is_inventory_manager or loan.phase != "draft":
            return jsonify({"error": "forbidden"}), 403
        try:
            if borrower_user_id == loan.borrower_user_id:
                pass
            elif (
                loan.contact_user_id == user.id
                and loan.borrower_user_id != user.id
            ):
                loan = update_loan(
                    session,
                    loan,
                    borrower_user_id=borrower_user_id,
                    manager_edit=True,
                    allow_shared_meta=True,
                )
            elif loan.borrower_user_id == user.id and borrower_user_id != user.id:
                loan = hand_draft_to_borrower(
                    session, loan, borrower_user_id=borrower_user_id, actor=user
                )
            else:
                loan = update_loan(
                    session,
                    loan,
                    borrower_user_id=borrower_user_id,
                    manager_edit=True,
                    allow_shared_meta=True,
                )
        except ValueError as exc:
            return _loan_error(exc)
        return jsonify(loan_detail_to_json(loan, viewer=user, session=session))
    if body.get("clearEvent") is True:
        if not can_edit_draft_meta():
            return jsonify({"error": "invalid_loan_state"}), 409
        kwargs["clear_event"] = True
        mark_manager_edit()
    elif "eventName" in body:
        event_name = body["eventName"]
        if event_name is not None and not isinstance(event_name, str):
            return jsonify({"error": "invalid_event"}), 400
        if not can_edit_draft_meta():
            return jsonify({"error": "invalid_loan_state"}), 409
        kwargs["event_name"] = event_name
        mark_manager_edit()
    if "wishPickupOn" in body or "wishReturnOn" in body:
        if loan.phase == "draft":
            if not is_borrower and not can_edit_draft_meta():
                return jsonify({"error": "invalid_loan_state"}), 409
        elif not manager_powers:
            return jsonify({"error": "invalid_loan_state"}), 409
        else:
            kwargs["manager_edit"] = True
    if "wishPickupOn" in body:
        try:
            kwargs["wish_pickup_on"] = parse_date(body.get("wishPickupOn"))
            kwargs["update_wish_pickup_on"] = True
        except ValueError:
            return jsonify({"error": "invalid_date"}), 400
    if "wishReturnOn" in body:
        try:
            kwargs["wish_return_on"] = parse_date(body.get("wishReturnOn"))
            kwargs["update_wish_return_on"] = True
        except ValueError:
            return jsonify({"error": "invalid_date"}), 400
    if "pickupOn" in body or "returnOn" in body:
        if not manager_powers and not manager_draft_for_other:
            return jsonify({"error": "forbidden"}), 403
    if "pickupOn" in body:
        try:
            kwargs["pickup_on"] = parse_date(body.get("pickupOn"))
            kwargs["update_pickup_on"] = True
            kwargs["manager_edit"] = True
        except ValueError:
            return jsonify({"error": "invalid_date"}), 400
    if "returnOn" in body:
        try:
            kwargs["return_on"] = parse_date(body.get("returnOn"))
            kwargs["update_return_on"] = True
            kwargs["manager_edit"] = True
        except ValueError:
            return jsonify({"error": "invalid_date"}), 400
    if "kind" in body:
        if not can_edit_draft_meta():
            return jsonify({"error": "invalid_loan_state"}), 409
        mark_manager_edit()
        kind = body["kind"]
        if not isinstance(kind, str):
            return jsonify({"error": "invalid_kind"}), 400
        kwargs["kind"] = kind
    if "contactUserId" in body and (manager_powers or manager_draft_for_other):
        cid = body["contactUserId"]
        if cid is not None and not isinstance(cid, int):
            return jsonify({"error": "invalid_contact"}), 400
        kwargs["contact_user_id"] = cid
        kwargs["update_contact"] = True
        kwargs["manager_edit"] = True
    if "pickupNote" in body:
        if not manager_powers:
            return jsonify({"error": "forbidden"}), 403
        if not isinstance(body.get("pickupNote"), str):
            return jsonify({"error": "forbidden"}), 403
        kwargs["pickup_note"] = body.get("pickupNote")
        kwargs["update_pickup_note"] = True
    if "returnNote" in body:
        if not is_borrower and not manager_powers:
            return jsonify({"error": "forbidden"}), 403
        if not isinstance(body.get("returnNote"), str):
            return jsonify({"error": "forbidden"}), 403
        kwargs["return_note"] = body.get("returnNote")
        kwargs["update_return_note"] = True

    try:
        loan = update_loan(session, loan, **kwargs)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(
        loan_detail_to_json(loan, viewer=user, session=session)
    )


def _handle_request(session, loan, body, user):
    try:
        pickup_on = parse_date(body.get("pickupOn"))
        if pickup_on is None:
            pickup_on = parse_date(body.get("wishPickupOn"))
        return_on = parse_date(body.get("returnOn"))
        if return_on is None:
            return_on = parse_date(body.get("wishReturnOn"))
    except ValueError:
        raise ValueError("invalid_date") from None
    if pickup_on is None:
        pickup_on = loan.wish_pickup_on
    if return_on is None and loan.kind != "permanent":
        return_on = loan.wish_return_on
    if pickup_on is None:
        raise ValueError("pickup_required")
    return submit_loan_request(
        session, loan, pickup_on=pickup_on, return_on=return_on, actor=user
    )


def _handle_confirm(session, loan, body, user):
    line_ids = _line_ids_from_body(body)
    return confirm_lines(session, loan, line_ids, actor=user)


def _handle_decline(session, loan, body, user):
    entries = body.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_decline")
    return decline_lines(session, loan, entries, actor=user)


def _handle_replace(session, loan, body, user):
    original_line_id = body.get("originalLineId")
    reason = body.get("reason")
    replacement = body.get("replacement")
    if not isinstance(original_line_id, int) or not isinstance(reason, str):
        raise ValueError("invalid_replacement")
    if not isinstance(replacement, dict):
        raise ValueError("invalid_replacement")
    return replace_line(
        session,
        loan,
        original_line_id=original_line_id,
        reason=reason,
        replacement=replacement,
        actor=user,
    )


def _handle_withdraw(session, loan, body, user):
    return withdraw_lines(session, loan, _line_ids_from_body(body), actor=user)


def _handle_pack(session, loan, body, user):
    return pack_lines(session, loan, _line_ids_from_body(body), actor=user)


def _handle_unpack(session, loan, body, user):
    return unpack_lines(session, loan, _line_ids_from_body(body), actor=user)


def _handle_mark_not_packed(session, loan, body, user):
    entries = body.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_entry")
    return mark_not_packed(session, loan, entries, actor=user)


def _handle_pickup(session, loan, body, user):
    return pickup_lines(session, loan, _line_ids_from_body(body), actor=user)


def _handle_undo_pickup(session, loan, body, user):
    return undo_pickup_lines(session, loan, _line_ids_from_body(body), actor=user)


def _handle_mark_not_picked_up(session, loan, body, user):
    entries = body.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_entry")
    return mark_not_picked_up(session, loan, entries, actor=user)


def _handle_report_return(session, loan, body, user):
    return report_return_lines(session, loan, _line_ids_from_body(body), actor=user)


def _handle_restock(session, loan, body, user):
    entries = body.get("entries")
    if isinstance(entries, list) and entries:
        return restock_lines(session, loan, entries, actor=user)
    line_ids = _line_ids_from_body(body)
    return restock_lines(
        session,
        loan,
        [{"lineId": line_id} for line_id in line_ids],
        actor=user,
    )


def _handle_record_loss(session, loan, body, user):
    entries = body.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_entry")
    return record_loss_lines(session, loan, entries, actor=user)


def _action_invoke(user, loan_id: int, handler):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        loan = handler(session, loan, body, user)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(loan_detail_to_json(loan, viewer=user, session=session))


@loans_bp.post("/loans/<int:loan_id>/actions/request")
@require_login
def loan_action_request(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_request)


@loans_bp.post("/loans/<int:loan_id>/actions/notify-added")
@loans_bp.post("/loans/<int:loan_id>/actions/complete-step")
@require_login
def loan_action_complete_step(user, loan_id: int):
    def _handle_complete(session, loan, _body, user):
        return complete_loan_step(session, loan, actor=user)

    return _action_invoke(user, loan_id, _handle_complete)


@require_login
def loan_action_notify_added(user, loan_id: int):
    def _handle_notify(session, loan, _body, user):
        return notify_added_lines(session, loan, actor=user)

    return _action_invoke(user, loan_id, _handle_notify)


@loans_bp.post("/loans/<int:loan_id>/actions/confirm")
@require_login
def loan_action_confirm(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_confirm)


@loans_bp.post("/loans/<int:loan_id>/actions/decline")
@require_login
def loan_action_decline(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_decline)


@loans_bp.post("/loans/<int:loan_id>/actions/replace")
@require_login
def loan_action_replace(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_replace)


@loans_bp.post("/loans/<int:loan_id>/actions/withdraw")
@require_login
def loan_action_withdraw(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_withdraw)


@loans_bp.post("/loans/<int:loan_id>/actions/cancel")
@require_login
def loan_action_cancel(user, loan_id: int):
    def _handle_cancel(session, loan, _body, user):
        return cancel_unpacked_loan(session, loan, actor=user)

    return _action_invoke(user, loan_id, _handle_cancel)


@loans_bp.post("/loans/<int:loan_id>/actions/skip-pickup")
@require_login
def loan_action_skip_pickup(user, loan_id: int):
    def _handle_skip_pickup(session, loan, _body, user):
        return skip_pickup_to_return(session, loan, actor=user)

    return _action_invoke(user, loan_id, _handle_skip_pickup)


@loans_bp.post("/loans/<int:loan_id>/actions/pack")
@require_login
def loan_action_pack(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_pack)


@loans_bp.post("/loans/<int:loan_id>/actions/unpack")
@require_login
def loan_action_unpack(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_unpack)


@loans_bp.post("/loans/<int:loan_id>/actions/mark-not-packed")
@require_login
def loan_action_not_packed(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_mark_not_packed)


@loans_bp.post("/loans/<int:loan_id>/actions/pickup")
@require_login
def loan_action_pickup(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_pickup)


@loans_bp.post("/loans/<int:loan_id>/actions/undo-pickup")
@require_login
def loan_action_undo_pickup(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_undo_pickup)


@loans_bp.post("/loans/<int:loan_id>/actions/mark-not-picked-up")
@require_login
def loan_action_not_picked_up(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_mark_not_picked_up)


@loans_bp.post("/loans/<int:loan_id>/actions/report-return")
@require_login
def loan_action_report_return(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_report_return)


@loans_bp.post("/loans/<int:loan_id>/actions/restock")
@require_login
def loan_action_restock(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_restock)


@loans_bp.post("/loans/<int:loan_id>/actions/record-loss")
@require_login
def loan_action_loss(user, loan_id: int):
    return _action_invoke(user, loan_id, _handle_record_loss)


@loans_bp.post("/loans/<int:loan_id>/lines")
@require_login
def post_loan_line(user, loan_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    if loan.borrower_user_id != user.id and not user_can_manage_inventory(
        session, user, loan.inventory
    ):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
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
    return jsonify(loan_detail_to_json(loan, viewer=user, session=session)), 201


@loans_bp.delete("/loans/<int:loan_id>/lines/<int:line_id>")
@loans_bp.post("/loans/<int:loan_id>/lines/<int:line_id>/restore")
@require_login
def restore_loan_line(user, loan_id: int, line_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    line = next((ln for ln in loan.lines if ln.id == line_id), None)
    if line is None:
        return jsonify({"error": "invalid_line"}), 409
    if line.status == "withdrawn":
        if loan.borrower_user_id != user.id and not user_can_manage_inventory(
            session, user, loan.inventory
        ):
            return jsonify({"error": "forbidden"}), 403
    elif not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403
    try:
        loan = reopen_loan_line(session, loan, line_id, actor=user)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify(loan_detail_to_json(loan, viewer=user, session=session))


@require_login
def delete_loan_line(user, loan_id: int, line_id: int):
    session = get_session()
    loan, err = _require_loan_access(session, user, loan_id)
    if err:
        return err
    try:
        remove_line(session, loan, line_id)
    except ValueError as exc:
        return _loan_error(exc)
    return jsonify({"ok": True})
