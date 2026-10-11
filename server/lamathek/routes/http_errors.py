from collections.abc import Callable

from flask import jsonify


def error_response(exc: ValueError, status_for: Callable[[str], int]):
    code = str(exc)
    return jsonify({"error": code}), status_for(code)
