from functools import wraps

from flask import jsonify

from lamathek.auth import current_user
from lamathek.db import get_session
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
