from flask import Blueprint, jsonify, request

from lamathek.access import require_inventory_manager, require_login, require_superuser
from lamathek.db import get_session
from lamathek.routes.inventory_fields import inventory_location_from_body
from lamathek.serializers import inventory_to_json, user_to_json
from lamathek.services.photos import (
    cover_photo_id_for_inventory,
    cover_photo_ids_for_inventories,
)
from lamathek.services.inventories import (
    create_inventory,
    delete_inventory,
    inventory_by_id,
    list_inventories_for_user,
    permission_users,
    replace_permissions,
    update_inventory,
)

inventories_bp = Blueprint("inventories", __name__, url_prefix="/api")


@inventories_bp.get("/inventories")
@require_login
def list_inventories(user):
    session = get_session()
    inventories = list_inventories_for_user(session, user)
    covers = cover_photo_ids_for_inventories(session, [i.id for i in inventories])
    return jsonify(
        [
            inventory_to_json(i, cover_photo_id=covers.get(i.id))
            for i in inventories
        ]
    )


@inventories_bp.post("/inventories")
@require_superuser
def post_inventory(_user):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    try:
        location = inventory_location_from_body(body)
    except ValueError as exc:
        if str(exc) in ("invalid_field", "invalid_coordinates"):
            return jsonify({"error": str(exc)}), 400
        raise
    session = get_session()
    try:
        inventory = create_inventory(session, name, **location)
    except ValueError as exc:
        if str(exc) == "name_taken":
            return jsonify({"error": "name_taken"}), 409
        if str(exc) == "invalid_coordinates":
            return jsonify({"error": "invalid_coordinates"}), 400
        raise
    return jsonify(inventory_to_json(inventory)), 201


@inventories_bp.patch("/inventories/<int:inventory_id>")
@require_inventory_manager()
def patch_inventory(user, inventory):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    try:
        location = inventory_location_from_body(body)
    except ValueError as exc:
        if str(exc) in ("invalid_field", "invalid_coordinates"):
            return jsonify({"error": str(exc)}), 400
        raise
    session = get_session()
    try:
        inventory = update_inventory(session, inventory, name, **location)
    except ValueError as exc:
        if str(exc) == "name_taken":
            return jsonify({"error": "name_taken"}), 409
        if str(exc) == "invalid_coordinates":
            return jsonify({"error": "invalid_coordinates"}), 400
        raise
    cover = cover_photo_id_for_inventory(session, inventory.id)
    return jsonify(
        inventory_to_json(inventory, cover_photo_id=cover, include_photos=True)
    )


@inventories_bp.get("/inventories/<int:inventory_id>")
@require_inventory_manager()
def get_inventory(_user, inventory):
    session = get_session()
    cover = cover_photo_id_for_inventory(session, inventory.id)
    return jsonify(
        inventory_to_json(inventory, cover_photo_id=cover, include_photos=True)
    )


@inventories_bp.delete("/inventories/<int:inventory_id>")
@require_superuser
def remove_inventory(_user, inventory_id: int):
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    delete_inventory(session, inventory)
    return ("", 204)


@inventories_bp.get("/inventories/<int:inventory_id>/permissions")
@require_inventory_manager()
def get_permissions(_user, inventory):
    session = get_session()
    users = permission_users(session, inventory.id)
    return jsonify({"users": [user_to_json(u) for u in users]})


@inventories_bp.put("/inventories/<int:inventory_id>/permissions")
@require_inventory_manager()
def put_permissions(_user, inventory):
    body = request.get_json(silent=True) or {}
    user_ids = body.get("userIds")
    if not isinstance(user_ids, list) or not all(
        isinstance(uid, int) for uid in user_ids
    ):
        return jsonify({"error": "invalid_user_ids"}), 400
    session = get_session()
    try:
        ids = replace_permissions(session, inventory, user_ids)
    except ValueError as exc:
        if str(exc) == "cannot_clear_permissions":
            return jsonify({"error": "cannot_clear_permissions"}), 409
        if str(exc) == "invalid_user_ids":
            return jsonify({"error": "invalid_user_ids"}), 400
        raise
    users = permission_users(session, inventory.id)
    return jsonify(
        {
            "userIds": ids,
            "users": [user_to_json(u) for u in users],
        }
    )
