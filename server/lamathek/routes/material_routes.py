from datetime import date

from flask import Blueprint, jsonify, request

from lamathek.access import require_inventory_manager, require_login, require_superuser
from lamathek.db import get_session
from lamathek.serializers import (
    category_to_json,
    damage_to_json,
    material_type_to_json,
    piece_detail_to_json,
    piece_to_json,
    stock_to_json,
)
from lamathek.services.categories import list_categories
from lamathek.services.damages import create_damage, create_repair, damage_by_id
from lamathek.services.inventories import (
    user_can_manage_any_inventory,
    user_can_manage_inventory,
)
from lamathek.services.material import (
    create_material_type,
    create_piece,
    create_pieces_batch,
    delete_material_type,
    delete_piece,
    list_material_types,
    list_pieces,
    list_stocks,
    material_type_by_id,
    piece_by_id,
    set_stock_quantity,
    update_material_type,
    update_piece,
)

material_bp = Blueprint("material", __name__, url_prefix="/api")


def _parse_date(value) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("invalid_date") from None


def _damage_error(exc: ValueError):
    code = str(exc)
    status = 400
    if code == "not_found":
        status = 404
    if code in ("already_repaired",):
        status = 409
    return jsonify({"error": code}), status


def _material_type_error(exc: ValueError):
    code = str(exc)
    status = 400
    if code in ("not_found", "invalid_material_type"):
        status = 404
    if code == "tracking_locked":
        status = 409
    if code in ("piece_on_loan", "below_loaned"):
        status = 409
    if code in ("short_name_taken", "name_taken"):
        status = 409
    if code in ("set_conflict", "invalid_count", "invalid_name_pattern"):
        status = 400
    if code == "invalid_set":
        status = 404
    if code in ("unit_not_for_piece", "invalid_category"):
        status = 400
    return jsonify({"error": code}), status


def _optional_str(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_field")
    return value


def _category_args_from_body(body: dict) -> dict:
    result: dict = {}
    if "categoryId" in body:
        category_id = body.get("categoryId")
        if category_id is None:
            result["clear_category"] = True
        elif isinstance(category_id, int):
            result["category_id"] = category_id
        else:
            raise ValueError("invalid_category")
    elif "categoryName" in body:
        name = body.get("categoryName")
        if name is not None and not isinstance(name, str):
            raise ValueError("invalid_category")
        if isinstance(name, str) and name.strip():
            result["category_name"] = name
    return result


@material_bp.get("/categories")
@require_login
def get_categories(user):
    session = get_session()
    if not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    categories = list_categories(session)
    return jsonify([category_to_json(c) for c in categories])


@material_bp.get("/inventories/<int:inventory_id>/material-types")
@require_inventory_manager()
def get_material_types(_user, inventory):
    session = get_session()
    types = list_material_types(session, inventory.id)
    return jsonify([material_type_to_json(t) for t in types])


@material_bp.post("/inventories/<int:inventory_id>/material-types")
@require_inventory_manager()
def post_material_type(_user, inventory):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    tracking = body.get("tracking")
    variant_label = body.get("variantLabel")
    variant_values = body.get("variantValues")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid_name"}), 400
    if not isinstance(tracking, str):
        return jsonify({"error": "invalid_tracking"}), 400
    if variant_values is None:
        variant_values = []
    if not isinstance(variant_values, list):
        return jsonify({"error": "invalid_variant_values"}), 400
    consumable = body.get("consumable")
    if consumable is not None and not isinstance(consumable, bool):
        return jsonify({"error": "invalid_consumable"}), 400
    session = get_session()
    try:
        category_args = _category_args_from_body(body)
        material_type = create_material_type(
            session,
            inventory,
            name,
            tracking,
            variant_label,
            variant_values,
            short_name=_optional_str(body.get("shortName")),
            description=_optional_str(body.get("description")),
            unit=_optional_str(body.get("unit")),
            consumable=bool(consumable) if consumable is not None else False,
            **category_args,
        )
    except ValueError as exc:
        return _material_type_error(exc)
    return jsonify(material_type_to_json(material_type)), 201


@material_bp.delete("/material-types/<int:material_type_id>")
@require_superuser
def remove_material_type(_user, material_type_id: int):
    session = get_session()
    material_type = material_type_by_id(session, material_type_id)
    if material_type is None:
        return jsonify({"error": "not_found"}), 404
    delete_material_type(session, material_type)
    return ("", 204)


@material_bp.patch("/material-types/<int:material_type_id>")
@require_login
def patch_material_type(user, material_type_id: int):
    session = get_session()
    material_type = material_type_by_id(session, material_type_id)
    if material_type is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_type.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    name = body.get("name")
    tracking = body.get("tracking")
    variant_label = body.get("variantLabel")
    variant_values = body.get("variantValues")

    if variant_values is not None and not isinstance(variant_values, list):
        return jsonify({"error": "invalid_variant_values"}), 400

    consumable = body.get("consumable")
    if consumable is not None and not isinstance(consumable, bool):
        return jsonify({"error": "invalid_consumable"}), 400

    update_kwargs: dict = {
        "name": name if isinstance(name, str) else None,
        "tracking": tracking if isinstance(tracking, str) else None,
        "variant_label": variant_label if "variantLabel" in body else None,
        "variant_values": variant_values,
    }
    if "shortName" in body:
        update_kwargs["short_name_sent"] = True
        update_kwargs["short_name"] = _optional_str(body.get("shortName"))
    if "description" in body:
        update_kwargs["description_sent"] = True
        update_kwargs["description"] = _optional_str(body.get("description"))
    if "unit" in body:
        update_kwargs["unit_sent"] = True
        update_kwargs["unit"] = _optional_str(body.get("unit"))
    if consumable is not None:
        update_kwargs["consumable"] = consumable

    try:
        update_kwargs.update(_category_args_from_body(body))
        material_type = update_material_type(session, material_type, **update_kwargs)
    except ValueError as exc:
        return _material_type_error(exc)
    return jsonify(material_type_to_json(material_type))


@material_bp.get("/inventories/<int:inventory_id>/pieces")
@require_inventory_manager()
def get_pieces(_user, inventory):
    session = get_session()
    pieces = list_pieces(session, inventory.id)
    return jsonify([piece_to_json(p) for p in pieces])


@material_bp.post("/inventories/<int:inventory_id>/pieces")
@require_inventory_manager()
def post_piece(_user, inventory):
    body = request.get_json(silent=True) or {}
    material_type_id = body.get("materialTypeId")
    name = body.get("name")
    variant = body.get("variant")
    if not isinstance(material_type_id, int):
        return jsonify({"error": "invalid_material_type"}), 400
    session = get_session()
    try:
        piece = create_piece(session, inventory, material_type_id, name, variant)
    except ValueError as exc:
        return _material_type_error(exc)
    piece = piece_by_id(session, piece.id)
    return jsonify(piece_to_json(piece)), 201


@material_bp.post("/inventories/<int:inventory_id>/pieces/batch")
@require_inventory_manager()
def post_pieces_batch(_user, inventory):
    body = request.get_json(silent=True) or {}
    material_type_id = body.get("materialTypeId")
    count = body.get("count")
    name_pattern = body.get("namePattern")
    variant = body.get("variant") if "variant" in body else None
    set_id = body.get("setId")
    set_name = body.get("setName")
    set_short_name = body.get("setShortName")

    if not isinstance(material_type_id, int):
        return jsonify({"error": "invalid_material_type"}), 400
    if set_id is not None and not isinstance(set_id, int):
        return jsonify({"error": "invalid_set"}), 400
    if set_name is not None and not isinstance(set_name, str):
        return jsonify({"error": "invalid_name"}), 400
    if not isinstance(name_pattern, str):
        return jsonify({"error": "invalid_name_pattern"}), 400

    session = get_session()
    try:
        pieces, result_set_id = create_pieces_batch(
            session,
            inventory,
            material_type_id=material_type_id,
            count=count,
            name_pattern=name_pattern,
            variant=variant,
            set_id=set_id,
            set_name=set_name,
            set_short_name=set_short_name if isinstance(set_short_name, str) else None,
        )
    except ValueError as exc:
        return _material_type_error(exc)

    payload: dict = {"pieces": [piece_to_json(p) for p in pieces]}
    if result_set_id is not None:
        payload["setId"] = result_set_id
    return jsonify(payload), 201


@material_bp.get("/pieces/<int:piece_id>")
@require_login
def get_piece(user, piece_id: int):
    session = get_session()
    piece = piece_by_id(session, piece_id)
    if piece is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, piece.material_type.inventory):
        return jsonify({"error": "forbidden"}), 403
    return jsonify(piece_detail_to_json(piece))


@material_bp.post("/pieces/<int:piece_id>/damages")
@require_login
def post_piece_damage(user, piece_id: int):
    session = get_session()
    piece = piece_by_id(session, piece_id)
    if piece is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, piece.material_type.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    try:
        recorded_on = _parse_date(body.get("recordedOn"))
    except ValueError:
        return jsonify({"error": "invalid_date"}), 400
    if recorded_on is None:
        return jsonify({"error": "invalid_date"}), 400

    note = body.get("note")
    if note is not None and not isinstance(note, str):
        return jsonify({"error": "invalid_note"}), 400
    severe = body.get("severe")
    if not isinstance(severe, bool):
        return jsonify({"error": "invalid_severe"}), 400

    damage = create_damage(
        session,
        piece,
        recorded_on,
        note=note.strip() if isinstance(note, str) and note.strip() else None,
        severe=severe,
    )
    return jsonify(damage_to_json(damage)), 201


@material_bp.post("/damages/<int:damage_id>/repairs")
@require_login
def post_damage_repair(user, damage_id: int):
    session = get_session()
    damage = damage_by_id(session, damage_id)
    if damage is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, damage.piece.material_type.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    try:
        recorded_on = _parse_date(body.get("recordedOn"))
    except ValueError:
        return jsonify({"error": "invalid_date"}), 400
    if recorded_on is None:
        return jsonify({"error": "invalid_date"}), 400

    note = body.get("note")
    if note is not None and not isinstance(note, str):
        return jsonify({"error": "invalid_note"}), 400

    try:
        create_repair(
            session,
            damage,
            recorded_on,
            note=note.strip() if isinstance(note, str) and note.strip() else None,
        )
    except ValueError as exc:
        return _damage_error(exc)
    damage = damage_by_id(session, damage_id)
    return jsonify(damage_to_json(damage)), 201


@material_bp.patch("/pieces/<int:piece_id>")
@require_login
def patch_piece(user, piece_id: int):
    session = get_session()
    piece = piece_by_id(session, piece_id)
    if piece is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, piece.material_type.inventory):
        return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    try:
        piece = update_piece(
            session,
            piece,
            name=body.get("name") if isinstance(body.get("name"), str) else None,
            material_type_id=body.get("materialTypeId")
            if isinstance(body.get("materialTypeId"), int)
            else None,
            variant=body.get("variant") if "variant" in body else None,
        )
    except ValueError as exc:
        return _material_type_error(exc)
    return jsonify(piece_to_json(piece))


@material_bp.delete("/pieces/<int:piece_id>")
@require_superuser
def remove_piece(_user, piece_id: int):
    session = get_session()
    piece = piece_by_id(session, piece_id)
    if piece is None:
        return jsonify({"error": "not_found"}), 404
    try:
        delete_piece(session, piece)
    except ValueError as exc:
        return _material_type_error(exc)
    return ("", 204)


@material_bp.get("/inventories/<int:inventory_id>/stocks")
@require_inventory_manager()
def get_stocks(_user, inventory):
    session = get_session()
    rows = list_stocks(session, inventory.id)
    return jsonify([stock_to_json(mt, qty) for mt, qty in rows])


@material_bp.put("/inventories/<int:inventory_id>/stocks/<int:material_type_id>")
@require_inventory_manager()
def put_stock(_user, inventory, material_type_id: int):
    body = request.get_json(silent=True) or {}
    quantity = body.get("quantity")
    if not isinstance(quantity, int):
        return jsonify({"error": "invalid_quantity"}), 400
    session = get_session()
    try:
        material_type, qty = set_stock_quantity(
            session, inventory, material_type_id, quantity
        )
    except ValueError as exc:
        return _material_type_error(exc)
    return jsonify(stock_to_json(material_type, qty))
