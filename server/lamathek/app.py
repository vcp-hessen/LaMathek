import os
from pathlib import Path

from flask import Flask, send_from_directory

from lamathek.auth import init_auth, validate_dev_bypass_config
from lamathek.config import Config
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


def client_dist_dir() -> Path:
    """Built Vue client. Checkout layout is server/lamathek → repo/web/dist.

    pip install puts this module in site-packages, so the image sets
    LAMATHEK_STATIC_ROOT (Dockerfile copies the build to /app/web/dist).
    """
    override = os.environ.get("LAMATHEK_STATIC_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / "web" / "dist"


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)

    validate_dev_bypass_config(app)
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
            return {"error": "not found"}, 404
        if not static_root.is_dir():
            return {"error": "not found"}, 404
        file_path = static_root / path
        if file_path.is_file():
            return send_from_directory(static_root, path)
        return send_from_directory(static_root, "index.html")

    return app
