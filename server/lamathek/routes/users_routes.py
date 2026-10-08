from flask import Blueprint, jsonify, request
from sqlalchemy import select

from lamathek.access import require_superuser
from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.serializers import user_to_json
from lamathek.services.users import set_superuser, user_by_id

users_bp = Blueprint("users", __name__, url_prefix="/api")


@users_bp.get("/users")
@require_superuser
def list_users(_user):
    session = get_session()
    users = session.scalars(select(User).order_by(User.id)).all()
    return jsonify([user_to_json(u) for u in users])


@users_bp.patch("/users/<int:user_id>")
@require_superuser
def patch_user(_actor, user_id: int):
    body = request.get_json(silent=True) or {}
    if "isSuperuser" not in body or not isinstance(body["isSuperuser"], bool):
        return jsonify({"error": "invalid_is_superuser"}), 400

    session = get_session()
    target = user_by_id(session, user_id)
    if target is None:
        return jsonify({"error": "not_found"}), 404

    try:
        set_superuser(session, target, body["isSuperuser"])
    except ValueError as exc:
        if str(exc) == "cannot_remove_last_superuser":
            return jsonify({"error": "cannot_remove_last_superuser"}), 409
        raise

    session.refresh(target)
    return jsonify(user_to_json(target))
