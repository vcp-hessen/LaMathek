from flask import Blueprint, jsonify, request

from lamathek.access import require_inventory_manager, require_login, require_superuser
from lamathek.db import get_session
from lamathek.serializers import inventory_to_json
from lamathek.services.inventories import (
    create_inventory,
    inventory_by_id,
    list_inventories_for_user,
    permission_user_ids,
    rename_inventory,
    replace_permissions,
)

inventories_bp = Blueprint("inventories", __name__, url_prefix="/api")


@inventories_bp.get("/inventories")
@require_login
def list_inventories(user):
    session = get_session()
    inventories = list_inventories_for_user(session, user)
    return jsonify([inventory_to_json(i) for i in inventories])


@inventories_bp.post("/inventories")
@require_superuser
def post_inventory(_user):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    session = get_session()
    try:
        inventory = create_inventory(session, name)
    except ValueError as exc:
        if str(exc) == "name_taken":
            return jsonify({"error": "name_taken"}), 409
        raise
    return jsonify(inventory_to_json(inventory)), 201


@inventories_bp.patch("/inventories/<int:inventory_id>")
@require_inventory_manager()
def patch_inventory(user, inventory):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    session = get_session()
    try:
        inventory = rename_inventory(session, inventory, name)
    except ValueError as exc:
        if str(exc) == "name_taken":
            return jsonify({"error": "name_taken"}), 409
        raise
    return jsonify(inventory_to_json(inventory))


@inventories_bp.get("/inventories/<int:inventory_id>")
@require_inventory_manager()
def get_inventory(_user, inventory):
    return jsonify(inventory_to_json(inventory))


@inventories_bp.get("/inventories/<int:inventory_id>/permissions")
@require_superuser
def get_permissions(_user, inventory_id: int):
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"userIds": permission_user_ids(session, inventory_id)})


@inventories_bp.put("/inventories/<int:inventory_id>/permissions")
@require_superuser
def put_permissions(_user, inventory_id: int):
    body = request.get_json(silent=True) or {}
    user_ids = body.get("userIds")
    if not isinstance(user_ids, list) or not all(
        isinstance(uid, int) for uid in user_ids
    ):
        return jsonify({"error": "invalid_user_ids"}), 400
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    ids = replace_permissions(session, inventory, user_ids)
    return jsonify({"userIds": ids})
