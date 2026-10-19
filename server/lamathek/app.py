import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from lamathek.auth import init_auth, validate_dev_bypass_config
from lamathek.config import DEFAULT_SECRET_KEY, Config
from lamathek.db import init_db
from lamathek.routes.api import api_bp
from lamathek.routes.auth_routes import auth_bp
from lamathek.routes.inventories_routes import inventories_bp
from lamathek.routes.material_routes import material_bp
from lamathek.routes.loans_routes import loans_bp
from lamathek.routes.sets_routes import sets_bp
from lamathek.routes.geocode_routes import geocode_bp
from lamathek.routes.settings_routes import settings_bp
from lamathek.routes.users_routes import users_bp
from lamathek.routes.photo_routes import photos_bp
from lamathek.routes.mail_routes import mail_bp
from lamathek.routes.impersonation_routes import impersonation_bp
from lamathek.routes.audit_routes import audit_bp
from lamathek.routes.calendar_routes import calendar_bp
from lamathek.routes.dashboard_routes import dashboard_bp


def client_dist_dir() -> Path:
    """Built Vue client. Checkout layout is server/lamathek → repo/web/dist.

    pip install puts this module in site-packages, so the image sets
    LAMATHEK_STATIC_ROOT (Dockerfile copies the build to /app/web/dist).
    """
    override = os.environ.get("LAMATHEK_STATIC_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / "web" / "dist"


MAX_UPLOAD_BYTES = 25 * 1024 * 1024

_HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "file_too_large",
}


def validate_secret_key(app: Flask) -> None:
    """Refuse to run outside dev/test with the built-in session key (sessions could be forged)."""
    if app.config.get("DEBUG") or app.config.get("TESTING"):
        return
    secret = app.config.get("SECRET_KEY") or ""
    if not secret or secret == DEFAULT_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set to a random value in production.")


CSRF_HEADER = "X-Requested-With"
CSRF_HEADER_VALUE = "lamathek"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _register_csrf_guard(app: Flask) -> None:
    """State-changing /api requests must carry a custom header.

    Browsers only send custom headers cross-site after a CORS preflight, which
    this API never grants, so a forged form or image request is rejected even
    where SameSite=Lax does not apply (top-level POST, older browsers).
    """

    @app.before_request
    def _csrf_guard():
        if request.method in _SAFE_METHODS or not request.path.startswith("/api/"):
            return None
        if request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE:
            return jsonify({"error": "csrf_header_missing"}), 403
        return None


def _register_api_error_handlers(app: Flask) -> None:
    def _wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        if not _wants_json():
            return exc
        code = _HTTP_ERROR_CODES.get(exc.code or 500, "http_error")
        return jsonify({"error": code}), exc.code

    @app.errorhandler(Exception)
    def _unhandled(exc: Exception):
        if isinstance(exc, HTTPException):
            return _http_error(exc)
        if app.config.get("TESTING"):
            raise exc
        app.logger.exception("Unhandled error on %s", request.path)
        if not _wants_json():
            return "Internal Server Error", 500
        return jsonify({"error": "internal_error"}), 500


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config)
    # Explicit assignment: Flask pre-populates these keys, so setdefault is a no-op.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = str(
        app.config.get("FRONTEND_URL", "")
    ).startswith("https://")
    if app.config.get("MAX_CONTENT_LENGTH") is None:
        app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    # One reverse proxy (Coolify/Traefik) sets X-Forwarded-For/-Proto/-Host.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    validate_secret_key(app)
    validate_dev_bypass_config(app)
    _register_api_error_handlers(app)
    _register_csrf_guard(app)
    if app.config.get("TESTING"):
        from lamathek.testing import ApiTestClient

        app.test_client_class = ApiTestClient
    init_db(app)
    init_auth(app)

    app.register_blueprint(api_bp)
    app.register_blueprint(inventories_bp)
    app.register_blueprint(material_bp)
    app.register_blueprint(sets_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(geocode_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(mail_bp)
    app.register_blueprint(impersonation_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(dashboard_bp)

    static_root = client_dist_dir()

    @app.get("/")
    def spa_index():
        if not static_root.is_dir():
            return (
                "LaMathek API is running. Build the client into web/dist or use the "
                "Vite dev server.",
                200,
            )
        return send_from_directory(static_root, "index.html")

    @app.get("/<path:path>")
    def spa_static(path: str):
        if path.startswith("api/"):
            return {"error": "not_found"}, 404
        if not static_root.is_dir():
            return {"error": "not_found"}, 404
        file_path = static_root / path
        if file_path.is_file():
            return send_from_directory(static_root, path)
        return send_from_directory(static_root, "index.html")

    return app
