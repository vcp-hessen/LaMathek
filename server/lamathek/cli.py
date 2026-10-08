from lamathek.app import create_app


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=5001, debug=app.config["DEBUG"])
