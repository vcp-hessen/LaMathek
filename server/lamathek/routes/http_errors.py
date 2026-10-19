from collections.abc import Callable

from flask import jsonify


def error_response(exc: ValueError, status_for: Callable[[str], int]):
    """``{"error": code}``; errors that know more (availability conflicts) add it."""
    code = str(exc)
    body = {"error": code}
    details = getattr(exc, "details", None)
    if callable(details):
        body.update(details())
    return jsonify(body), status_for(code)
