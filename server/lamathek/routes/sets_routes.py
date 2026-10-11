from flask import Blueprint, jsonify, request

from lamathek.access import require_inventory_manager, require_login, require_superuser
from lamathek.db import get_session
from lamathek.serializers import set_detail_to_json, set_to_json
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.photos import cover_photo_ids_for_sets
from lamathek.services.sets import (
    create_set,
    delete_set,
    list_sets,
    set_by_id,
    set_piece_membership,
    update_set,
    upsert_stock_line,
)

sets_bp = Blueprint("sets", __name__, url_prefix="/api")


def _optional_str(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _set_error(exc: ValueError):
    code = str(exc)
    status = 400
    if code in ("not_found", "invalid_piece", "invalid_material_type"):
        status = 404
    if code in ("name_taken", "short_name_taken"):
        status = 409
    if code in ("over_reserved", "piece_on_other_set"):
        status = 409
    return jsonify({"error": code}), status


@sets_bp.get("/inventories/<int:inventory_id>/sets")
@require_inventory_manager()
def get_sets(_user, inventory):
    session = get_session()
    sets = list_sets(session, inventory.id)
    covers = cover_photo_ids_for_sets(session, [s.id for s in sets])
    return jsonify([set_to_json(s, cover_photo_id=covers.get(s.id)) for s in sets])


@sets_bp.post("/inventories/<int:inventory_id>/sets")
@require_inventory_manager()
def post_set(_user, inventory):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    session = get_session()
    short_name = _optional_str(body.get("shortName"))
    try:
        material_set = create_set(session, inventory, name, short_name=short_name)
    except ValueError as exc:
        return _set_error(exc)
    return jsonify(set_detail_to_json(material_set)), 201


@sets_bp.get("/sets/<int:set_id>")
@require_login
def get_set(user, set_id: int):
    session = get_session()
    material_set = set_by_id(session, set_id)
    if material_set is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_set.inventory):
        return jsonify({"error": "forbidden"}), 403
    covers = cover_photo_ids_for_sets(session, [material_set.id])
    return jsonify(
        set_detail_to_json(material_set, cover_photo_id=covers.get(material_set.id))
    )


@sets_bp.patch("/sets/<int:set_id>")
@require_login
def patch_set(user, set_id: int):
    session = get_session()
    material_set = set_by_id(session, set_id)
    if material_set is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_set.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    short_name_sent = "shortName" in body
    short_name = _optional_str(body.get("shortName")) if short_name_sent else None
    try:
        material_set = update_set(
            session,
            material_set,
            name=name,
            short_name=short_name,
            short_name_sent=short_name_sent,
        )
    except ValueError as exc:
        return _set_error(exc)
    return jsonify(set_detail_to_json(material_set))


@sets_bp.delete("/sets/<int:set_id>")
@require_superuser
def remove_set(_user, set_id: int):
    session = get_session()
    material_set = set_by_id(session, set_id)
    if material_set is None:
        return jsonify({"error": "not_found"}), 404
    delete_set(session, material_set)
    return ("", 204)


@sets_bp.put("/sets/<int:set_id>/pieces")
@require_login
def put_set_piece(user, set_id: int):
    session = get_session()
    material_set = set_by_id(session, set_id)
    if material_set is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_set.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    piece_id = body.get("pieceId")
    role = body.get("role")
    if not isinstance(piece_id, int):
        return jsonify({"error": "invalid_piece"}), 400
    if role is not None and role not in ("assignment", "optional"):
        return jsonify({"error": "invalid_role"}), 400

    try:
        set_piece_membership(session, material_set, piece_id, role)
    except ValueError as exc:
        return _set_error(exc)

    from lamathek.serializers import piece_to_json
    from lamathek.services.material import piece_by_id

    piece = piece_by_id(session, piece_id)
    return jsonify(piece_to_json(piece))


@sets_bp.put("/sets/<int:set_id>/stock-lines")
@require_login
def put_set_stock_line(user, set_id: int):
    session = get_session()
    material_set = set_by_id(session, set_id)
    if material_set is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_set.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    material_type_id = body.get("materialTypeId")
    role = body.get("role")
    quantity = body.get("quantity")
    if not isinstance(material_type_id, int):
        return jsonify({"error": "invalid_material_type"}), 400
    if role not in ("assignment", "optional"):
        return jsonify({"error": "invalid_role"}), 400
    if not isinstance(quantity, int):
        return jsonify({"error": "invalid_quantity"}), 400

    try:
        line = upsert_stock_line(
            session, material_set, material_type_id, role, quantity
        )
    except ValueError as exc:
        return _set_error(exc)

    material_set = set_by_id(session, set_id)
    return jsonify(set_detail_to_json(material_set))
