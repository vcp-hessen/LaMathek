import argparse
import os
from importlib import resources

from lamathek.config import Config


def alembic_config(database_url: str | None = None):
    """Alembic config for the packaged migrations, bound to the app's database."""
    from alembic.config import Config as AlembicConfig

    script_location = resources.files("lamathek") / "migrations"
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option(
        "sqlalchemy.url",
        (database_url or Config.SQLALCHEMY_DATABASE_URI).replace("%", "%%"),
    )
    return cfg


def upgrade_database(database_url: str | None = None) -> None:
    """Apply Alembic migrations to the same database the app will open."""
    from alembic import command

    command.upgrade(alembic_config(database_url), "head")


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _run_dev_server() -> None:
    from lamathek.app import create_app

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


def main() -> None:
    parser = argparse.ArgumentParser(prog="lamathek")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="Migrate, then run the development server (default).")
    sub.add_parser("migrate", help="Apply database migrations and exit.")
    sub.add_parser(
        "openapi", help="Write lamathek/domain/openapi.json from the response models."
    )
    args = parser.parse_args()

    if args.command == "migrate":
        upgrade_database()
        return
    if args.command == "openapi":
        from lamathek.contract.openapi import write_openapi

        print(write_openapi())
        return
    _run_dev_server()
