import os

from lamathek.app import create_app


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
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
