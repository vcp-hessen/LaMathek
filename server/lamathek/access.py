from functools import wraps

from flask import jsonify

from lamathek.auth import current_user
from lamathek.db import get_session
from lamathek.services.inventories import inventory_by_id, user_can_manage_inventory
from lamathek.services.users import user_by_oidc_sub


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        session_user = current_user()
        if session_user is None or not session_user.get("sub"):
            return jsonify({"error": "unauthorized"}), 401
        db = get_session()
        user = user_by_oidc_sub(db, session_user["sub"])
        if user is None:
            return jsonify({"error": "unauthorized"}), 401
        return fn(user, *args, **kwargs)

    return wrapper


def require_superuser(fn):
    @wraps(fn)
    @require_login
    def wrapper(user, *args, **kwargs):
        if not user.is_superuser:
            return jsonify({"error": "forbidden"}), 403
        return fn(user, *args, **kwargs)

    return wrapper


def require_inventory_manager(inventory_id_kwarg: str = "inventory_id"):
    def decorator(fn):
        @wraps(fn)
        @require_login
        def wrapper(user, *args, **kwargs):
            inventory_id = kwargs.get(inventory_id_kwarg)
            if inventory_id is None:
                return jsonify({"error": "not_found"}), 404
            db = get_session()
            inventory = inventory_by_id(db, inventory_id)
            if inventory is None:
                return jsonify({"error": "not_found"}), 404
            if not user_can_manage_inventory(db, user, inventory):
                return jsonify({"error": "forbidden"}), 403
            kwargs.pop(inventory_id_kwarg, None)
            return fn(user, inventory, *args, **kwargs)

        return wrapper

    return decorator
