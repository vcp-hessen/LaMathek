import os

from lamathek.app import create_app


def main() -> None:
    app = create_app()
    port = int(os.environ.get("LAMATHEK_API_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=app.config["DEBUG"])
