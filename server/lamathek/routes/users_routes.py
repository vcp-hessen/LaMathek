from flask import Blueprint, jsonify, request
from sqlalchemy import select

from lamathek.access import require_login, require_superuser
from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.serializers import user_to_json
from lamathek.services.inventories import user_can_manage_any_inventory
from lamathek.services.users import search_users, set_superuser, user_by_id

users_bp = Blueprint("users", __name__, url_prefix="/api")


def _require_can_grant_permissions(user):
    session = get_session()
    if not user_can_manage_any_inventory(session, user):
        return jsonify({"error": "forbidden"}), 403
    return None


@users_bp.get("/users")
@require_superuser
def list_users(_user):
    session = get_session()
    users = session.scalars(select(User).order_by(User.id)).all()
    return jsonify([user_to_json(u) for u in users])


@users_bp.get("/users/search")
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
    return jsonify([user_to_json(u) for u in users])


@users_bp.patch("/users/<int:user_id>")
@require_superuser
def patch_user(_actor, user_id: int):
    body = request.get_json(silent=True) or {}
    if "isSuperuser" not in body:
        return jsonify({"error": "nothing_to_update"}), 400

    session = get_session()
    target = user_by_id(session, user_id)
    if target is None:
        return jsonify({"error": "not_found"}), 404

    if not isinstance(body["isSuperuser"], bool):
        return jsonify({"error": "invalid_is_superuser"}), 400
    try:
        set_superuser(session, target, body["isSuperuser"])
    except ValueError as exc:
        if str(exc) == "cannot_remove_last_superuser":
            return jsonify({"error": "cannot_remove_last_superuser"}), 409
        raise

    session.refresh(target)
    return jsonify(user_to_json(target))
