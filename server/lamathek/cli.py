import os

from lamathek.app import create_app
from lamathek.config import Config, checkout_root


def upgrade_database() -> None:
    """Apply Alembic migrations to the same database the app will open."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    ini = checkout_root() / "server" / "alembic.ini"
    cfg = AlembicConfig(str(ini))
    cfg.set_main_option("script_location", str(ini.parent / "alembic"))
    cfg.set_main_option(
        "sqlalchemy.url",
        Config.SQLALCHEMY_DATABASE_URI.replace("%", "%%"),
    )
    command.upgrade(cfg, "head")


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    upgrade_database()
    app = create_app()
    port = int(os.environ.get("PORT") or os.environ.get("LAMATHEK_API_PORT") or "5001")
    host = os.environ.get("LAMATHEK_BIND_HOST", "127.0.0.1")
    reload_requested = _env_flag("LAMATHEK_RELOAD")
    debug = bool(app.config["DEBUG"])
    app.run(
        host=host,
        port=port,
        debug=debug or reload_requested,
        use_reloader=debug or reload_requested,
        use_debugger=debug and not reload_requested,
    )
