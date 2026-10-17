from flask import Blueprint, jsonify, request, send_file

from lamathek.access import require_login
from lamathek.db import get_session
from lamathek.services.inventories import (
    user_can_manage_inventory,
    user_can_view_inventory,
)
from lamathek.services.material import piece_by_id, stock_lot_by_id, material_type_by_id
from lamathek.services.damages import damage_by_id
from lamathek.services.inventories import inventory_by_id
from lamathek.services.loans import loan_by_id
from lamathek.services.sets import set_by_id
from lamathek.services.photo_storage import ALLOWED_UPLOAD_MIME, resolve_served_path
from lamathek.services.photos import (
    add_photo,
    delete_photo,
    inventory_for_photo,
    photo_by_id,
    set_cover_photo,
)

from lamathek.routes.http_errors import error_response

photos_bp = Blueprint("photos", __name__, url_prefix="/api")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _photo_status(code: str) -> int:
    status = 400
    if code == "not_found":
        status = 404
    return status


def _photo_json_error(exc: ValueError):
    return error_response(exc, _photo_status)


def _require_photo_view(user, photo):
    session = get_session()
    inventory = inventory_for_photo(session, photo)
    if inventory is None:
        return None, (jsonify({"error": "not_found"}), 404)
    if not user_can_view_inventory(session, user, inventory):
        return None, (jsonify({"error": "forbidden"}), 403)
    return inventory, None


def _require_photo_manage(user, photo):
    session = get_session()
    inventory = inventory_for_photo(session, photo)
    if inventory is None:
        return None, (jsonify({"error": "not_found"}), 404)
    if not user_can_manage_inventory(session, user, inventory):
        return None, (jsonify({"error": "forbidden"}), 403)
    return inventory, None


def _read_upload_file():
    if "file" not in request.files:
        return None, (jsonify({"error": "missing_file"}), 400)
    upload = request.files["file"]
    if not upload or not upload.filename:
        return None, (jsonify({"error": "missing_file"}), 400)
    content_type = (upload.mimetype or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_UPLOAD_MIME:
        return None, (jsonify({"error": "invalid_image_type"}), 400)
    raw = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        return None, (jsonify({"error": "file_too_large"}), 400)
    if not raw:
        return None, (jsonify({"error": "empty_file"}), 400)
    return raw, None


@photos_bp.get("/photos/<int:photo_id>")
@require_login
def get_photo_file(user, photo_id: int):
    session = get_session()
    photo = photo_by_id(session, photo_id)
    if photo is None:
        return jsonify({"error": "not_found"}), 404
    _, err = _require_photo_view(user, photo)
    if err:
        return err

    size = request.args.get("size", "640")
    if size not in {"160", "640", "full"}:
        return jsonify({"error": "invalid_size"}), 400
    path = resolve_served_path(photo_id, size)
    if path is None:
        return jsonify({"error": "not_found"}), 404
    return send_file(path, mimetype="image/webp", max_age=86400)


@photos_bp.delete("/photos/<int:photo_id>")
@require_login
def remove_photo(user, photo_id: int):
    session = get_session()
    photo = photo_by_id(session, photo_id)
    if photo is None:
        return jsonify({"error": "not_found"}), 404
    _, err = _require_photo_manage(user, photo)
    if err:
        return err
    delete_photo(session, photo)
    return "", 204


@photos_bp.post("/photos/<int:photo_id>/make-cover")
@require_login
def make_cover(user, photo_id: int):
    session = get_session()
    photo = photo_by_id(session, photo_id)
    if photo is None:
        return jsonify({"error": "not_found"}), 404
    _, err = _require_photo_manage(user, photo)
    if err:
        return err
    try:
        photo = set_cover_photo(session, photo)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order})


@photos_bp.post("/pieces/<int:piece_id>/photos")
@require_login
def upload_piece_photo(user, piece_id: int):
    session = get_session()
    piece = piece_by_id(session, piece_id)
    if piece is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, piece.material_type.inventory):
        return jsonify({"error": "forbidden"}), 403
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(session, raw_bytes=raw, piece_id=piece_id)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201


@photos_bp.post("/inventories/<int:inventory_id>/stock-lots/<int:lot_id>/photos")
@require_login
def upload_stock_lot_photo(user, inventory_id: int, lot_id: int):
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, inventory):
        return jsonify({"error": "forbidden"}), 403
    lot = stock_lot_by_id(session, lot_id)
    if lot is None or lot.material_type.inventory_id != inventory_id:
        return jsonify({"error": "not_found"}), 404
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(session, raw_bytes=raw, stock_lot_id=lot_id)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201


@photos_bp.post("/sets/<int:set_id>/photos")
@require_login
def upload_set_photo(user, set_id: int):
    session = get_session()
    material_set = set_by_id(session, set_id)
    if material_set is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_set.inventory):
        return jsonify({"error": "forbidden"}), 403
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(session, raw_bytes=raw, set_id=set_id)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201


@photos_bp.post("/material-types/<int:material_type_id>/photos")
@require_login
def upload_material_type_photo(user, material_type_id: int):
    session = get_session()
    material_type = material_type_by_id(session, material_type_id)
    if material_type is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, material_type.inventory):
        return jsonify({"error": "forbidden"}), 403
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(session, raw_bytes=raw, material_type_id=material_type_id)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201


@photos_bp.post("/damages/<int:damage_id>/photos")
@require_login
def upload_damage_photo(user, damage_id: int):
    session = get_session()
    damage = damage_by_id(session, damage_id)
    if damage is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, damage.piece.material_type.inventory):
        return jsonify({"error": "forbidden"}), 403
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(session, raw_bytes=raw, damage_id=damage_id)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201


@photos_bp.post("/inventories/<int:inventory_id>/photos")
@require_login
def upload_inventory_photo(user, inventory_id: int):
    session = get_session()
    inventory = inventory_by_id(session, inventory_id)
    if inventory is None:
        return jsonify({"error": "not_found"}), 404
    if not user_can_manage_inventory(session, user, inventory):
        return jsonify({"error": "forbidden"}), 403
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(session, raw_bytes=raw, inventory_id=inventory_id)
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201


@photos_bp.post("/loans/<int:loan_id>/photos")
@require_login
def upload_loan_photo(user, loan_id: int):
    session = get_session()
    loan = loan_by_id(session, loan_id)
    if loan is None:
        return jsonify({"error": "not_found"}), 404
    from lamathek.services.loan_access import user_can_view_loan

    if not user_can_view_loan(session, user, loan):
        return jsonify({"error": "forbidden"}), 403
    role = request.args.get("role", "loan")
    if role not in ("loan", "pickup", "return"):
        return jsonify({"error": "invalid_role"}), 400
    if role == "pickup" and not user_can_manage_inventory(session, user, loan.inventory):
        return jsonify({"error": "forbidden"}), 403
    raw, err = _read_upload_file()
    if err:
        return err
    try:
        photo = add_photo(
            session, raw_bytes=raw, loan_id=loan_id, loan_photo_role=role
        )
    except ValueError as exc:
        return _photo_json_error(exc)
    return jsonify({"id": photo.id, "sortOrder": photo.sort_order}), 201
