from functools import wraps

from flask import g, jsonify, session

from lamathek.auth import session_actor_sub, session_impersonation
from lamathek.db import get_session
from lamathek.services.inventories import (
    inventory_by_id,
    user_can_manage_inventory,
    user_can_view_inventory,
)
from lamathek.services.users import user_by_oidc_sub


def resolve_request_user(db):
    """User the request acts as, re-checking an active impersonation every time.

    The signed-in actor must still exist and still be a superuser, and the target
    must not have become one; otherwise the impersonation ends silently and the
    request runs as the actor. ``g.real_actor`` is the superuser while
    impersonating, so the journal can name who actually acted.
    """
    g.real_actor = None
    actor_sub = session_actor_sub()
    if not actor_sub:
        return None
    actor = user_by_oidc_sub(db, actor_sub)
    if actor is None:
        session.pop("impersonation", None)
        return None
    imp = session_impersonation()
    if imp is None:
        return actor
    target = user_by_oidc_sub(db, imp.get("sub") or "")
    if not actor.is_superuser or target is None or target.is_superuser:
        session.pop("impersonation", None)
        return actor
    g.real_actor = actor
    return target


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = resolve_request_user(get_session())
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


def require_inventory_viewer(inventory_id_kwarg: str = "inventory_id"):
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
            if not user_can_view_inventory(db, user, inventory):
                return jsonify({"error": "forbidden"}), 403
            kwargs.pop(inventory_id_kwarg, None)
            return fn(user, inventory, *args, **kwargs)

        return wrapper

    return decorator
