from pathlib import Path

from flask import Flask, send_from_directory

from lamathek.auth import init_auth, validate_dev_bypass_config
from lamathek.config import Config
from lamathek.db import init_db
from lamathek.routes.api import api_bp
from lamathek.routes.auth_routes import auth_bp
from lamathek.routes.settings_routes import settings_bp
from lamathek.routes.users_routes import users_bp


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)

    validate_dev_bypass_config(app)
    init_db(app)
    init_auth(app)

    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)

    static_root = Path(__file__).resolve().parent.parent.parent / "web" / "dist"

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
