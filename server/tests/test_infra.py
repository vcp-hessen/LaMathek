"""App bootstrap: secret guard, JSON API errors, env file precedence, packaged data."""

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from conftest import app_with_db
from lamathek.app import create_app
from lamathek.config import DEFAULT_SECRET_KEY, Config


def _config(**overrides):
    tmp = tempfile.mkdtemp()
    attrs = {
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{os.path.join(tmp, 'x.sqlite3')}",
        "TESTING": False,
        "DEBUG": False,
        **overrides,
    }
    return type("Cfg", (Config,), attrs)


def test_production_refuses_default_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(_config(SECRET_KEY=DEFAULT_SECRET_KEY))


def test_production_accepts_explicit_secret_key():
    app = create_app(_config(SECRET_KEY="a-real-random-value"))
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["MAX_CONTENT_LENGTH"] == 25 * 1024 * 1024


def test_secure_cookie_follows_https_frontend():
    app = create_app(_config(SECRET_KEY="x" * 32, FRONTEND_URL="https://lamathek.example"))
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_unknown_api_route_returns_json_404():
    app, tmp = app_with_db()
    try:
        response = app.test_client().get("/api/does-not-exist")
        assert response.status_code == 404
        assert response.get_json() == {"error": "not_found"}
        response = app.test_client().delete("/api/health")
        assert response.status_code == 405
        assert response.get_json() == {"error": "method_not_allowed"}
    finally:
        tmp.cleanup()


def _load_config_in_subprocess(repo: Path, env: dict, *, skip: bool = False) -> str:
    """Import lamathek.config with a fake repo root and print the resolved SMTP host."""
    code = textwrap.dedent(
        """
        import lamathek.config as c
        from pathlib import Path
        import os, sys
        c.REPO_ROOT = Path(sys.argv[1])
        os.environ["LAMATHEK_SKIP_DOTENV"] = sys.argv[2]
        c.load_env_files()
        print(os.environ.get("SMTP_HOST", ""))
        """
    )
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("SMTP_", "LAMATHEK_"))}
    result = subprocess.run(
        [sys.executable, "-c", code, str(repo), "1" if skip else "0"],
        # Skip at import time so the real checkout's .env files are never read.
        env={**clean, "LAMATHEK_SKIP_DOTENV": "1", **env},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_env_local_overrides_env_dev_in_dev_mode(tmp_path):
    (tmp_path / ".env.dev").write_text("SMTP_HOST=from-dev\n")
    (tmp_path / ".env.local").write_text("SMTP_HOST=from-local\n")
    host = _load_config_in_subprocess(tmp_path, {"LAMATHEK_ENV": "dev"})
    assert host == "from-local"


def test_skip_dotenv_ignores_env_files(tmp_path):
    (tmp_path / ".env.dev").write_text("SMTP_HOST=from-dev\n")
    host = _load_config_in_subprocess(tmp_path, {"LAMATHEK_ENV": "dev"}, skip=True)
    assert host == ""


def test_package_data_is_importable_from_package_resources():
    from importlib import resources

    from lamathek.services.workflow_gates import workflow_gates

    assert workflow_gates()["lineActions"]
    root = resources.files("lamathek")
    for rel in (
        "domain/workflow_gates.json",
        "i18n/de.json",
        "static/fonts/Roboto-Regular.ttf",
        "templates/pdf/base.html",
        "migrations/env.py",
    ):
        assert (root / rel).is_file(), rel
