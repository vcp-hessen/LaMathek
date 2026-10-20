from flask import Blueprint, jsonify, request
from sqlalchemy import select

from lamathek.contract import models as api, responds
from lamathek.access import require_login, require_superuser
from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.serializers import user_to_json
from lamathek.services.inventories import (
    grant_inventory_permission,
    inventory_by_id,
    inventory_ids_by_user,
    revoke_inventory_permission,
    user_can_manage_any_inventory,
)
from lamathek.services.audit import record_audit_event
from lamathek.models.audit import AUDIT_USER_MERGED
from lamathek.services.loan_access import user_can_edit_contact
from lamathek.services.users import (
    create_local_user,
    merge_local_user_into_login,
    search_users,
    set_superuser,
    update_user_contact,
    user_by_id,
)

users_bp = Blueprint("users", __name__, url_prefix="/api")


def _require_can_grant_permissions(user):
    session = get_session()
    if not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    return None


def _managed_user_json(
    user: User, inventory_ids: list[int], *, can_edit_contact: bool = True
) -> dict:
    body = user_to_json(user, include_phone=can_edit_contact)
    body["inventoryIds"] = inventory_ids
    body["canEditContact"] = can_edit_contact
    return body


@users_bp.post("/users")
@responds(api.User, status=201)
@require_login
def post_local_user(user):
    denied = _require_can_grant_permissions(user)
    if denied is not None:
        return denied
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    phone = body.get("phone")
    email = body.get("email")
    if not isinstance(name, str) or not isinstance(phone, str):
        return jsonify({"error": "invalid_user"}), 400
    if not isinstance(email, str):
        return jsonify({"error": "invalid_user"}), 400
    session = get_session()
    try:
        created = create_local_user(session, name=name, phone=phone, email=email)
    except ValueError as exc:
        if str(exc) == "invalid_user":
            return jsonify({"error": "invalid_user"}), 400
        if str(exc) == "email_taken":
            return jsonify({"error": "email_taken"}), 409
        raise
    return jsonify(user_to_json(created)), 201


@users_bp.get("/users")
@responds(list[api.ManagedUser])
@require_login
def list_users(user):
    session = get_session()
    if not user.is_superuser and not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    users = session.scalars(select(User).order_by(User.id)).all()
    by_user = inventory_ids_by_user(session)
    # Phones only where the viewer may edit them (D0005); superusers see all.
    return jsonify(
        [
            _managed_user_json(
                u,
                by_user.get(u.id, []),
                can_edit_contact=user_can_edit_contact(session, user, u),
            )
            for u in users
        ]
    )


@users_bp.get("/users/search")
@responds(list[api.User])
@require_login
def search_users_route(user):
    denied = _require_can_grant_permissions(user)
    if denied is not None:
        return denied
    query = request.args.get("q", "")
    if not isinstance(query, str):
        query = ""
    session = get_session()
    users = search_users(session, query)
    return jsonify([user_to_json(u, include_phone=False) for u in users])


@users_bp.patch("/users/<int:user_id>")
@responds(api.User)
@require_login
def patch_user(actor, user_id: int):
    body = request.get_json(silent=True) or {}
    session = get_session()
    target = user_by_id(session, user_id)
    if target is None:
        return jsonify({"error": "not_found"}), 404

    phone = body.get("phone") if "phone" in body else None
    email = body.get("email") if "email" in body else None
    if phone is not None and not isinstance(phone, str):
        return jsonify({"error": "invalid_user"}), 400
    if email is not None and not isinstance(email, str):
        return jsonify({"error": "invalid_user"}), 400
    if "isSuperuser" not in body and phone is None and email is None:
        return jsonify({"error": "nothing_to_update"}), 400
    if "isSuperuser" in body:
        if not actor.is_superuser:
            return jsonify({"error": "forbidden"}), 403
        if not isinstance(body["isSuperuser"], bool):
            return jsonify({"error": "invalid_is_superuser"}), 400
    if (phone is not None or email is not None) and not user_can_edit_contact(
        session, actor, target
    ):
        return jsonify({"error": "forbidden"}), 403

    if "isSuperuser" in body:
        try:
            set_superuser(session, target, body["isSuperuser"])
        except ValueError as exc:
            if str(exc) == "cannot_remove_last_superuser":
                return jsonify({"error": "cannot_remove_last_superuser"}), 409
            raise
    if phone is not None or email is not None:
        try:
            update_user_contact(session, target, phone=phone, email=email)
        except ValueError as exc:
            code = str(exc)
            if code == "invalid_user":
                return jsonify({"error": "invalid_user"}), 400
            if code == "email_taken":
                return jsonify({"error": "email_taken"}), 409
            raise

    session.refresh(target)
    return jsonify(user_to_json(target))


@users_bp.post("/users/<int:user_id>/inventories")
@responds(api.ManagedUser)
@require_superuser
def grant_user_inventory(_actor, user_id: int):
    body = request.get_json(silent=True) or {}
    inventory_id = body.get("inventoryId")
    if not isinstance(inventory_id, int):
        return jsonify({"error": "invalid_inventory_id"}), 400

    session = get_session()
    target = user_by_id(session, user_id)
    inventory = inventory_by_id(session, inventory_id)
    if target is None or inventory is None:
        return jsonify({"error": "not_found"}), 404

    try:
        inventory_ids = grant_inventory_permission(session, target, inventory)
    except ValueError as exc:
        if str(exc) == "local_user":
            return jsonify({"error": "local_user"}), 409
        raise
    return jsonify(_managed_user_json(target, inventory_ids))


@users_bp.delete("/users/<int:user_id>/inventories/<int:inventory_id>")
@responds(api.ManagedUser)
@require_superuser
def revoke_user_inventory(_actor, user_id: int, inventory_id: int):
    session = get_session()
    target = user_by_id(session, user_id)
    inventory = inventory_by_id(session, inventory_id)
    if target is None or inventory is None:
        return jsonify({"error": "not_found"}), 404

    try:
        inventory_ids = revoke_inventory_permission(session, target, inventory)
    except ValueError as exc:
        if str(exc) == "cannot_clear_permissions":
            return jsonify({"error": "cannot_clear_permissions"}), 409
        raise

    return jsonify(_managed_user_json(target, inventory_ids))


@users_bp.post("/users/<int:user_id>/merge")
@responds(api.User)
@require_superuser
def merge_user(user, user_id: int):
    session = get_session()
    body = request.get_json(silent=True) or {}
    target_id = body.get("targetUserId")
    if not isinstance(target_id, int):
        return jsonify({"error": "invalid_merge"}), 400
    try:
        target = merge_local_user_into_login(
            session, source_id=user_id, target_id=target_id
        )
    except ValueError as exc:
        code = str(exc)
        if code == "not_found":
            return jsonify({"error": "not_found"}), 404
        if code == "invalid_merge":
            return jsonify({"error": "invalid_merge"}), 409
        raise
    record_audit_event(
        session,
        actor_user_id=user.id,
        action=AUDIT_USER_MERGED,
        target_user_id=target.id,
        detail={"mergedUserId": user_id},
    )
    return jsonify(user_to_json(target))
