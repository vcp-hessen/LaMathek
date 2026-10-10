import os
from pathlib import Path

from dotenv import load_dotenv


def checkout_root() -> Path:
    """Repository root in a checkout, or /app inside the staging image.

    After pip install this file lives in site-packages, so walking up from
    __file__ is not the checkout. Alembic is launched from the copied sources
    and would otherwise migrate a different SQLite file than the running app.
    """
    candidate = Path(__file__).resolve().parents[2]
    marker = candidate / "server" / "alembic.ini"
    if marker.is_file() and (candidate / "web").is_dir():
        return candidate
    image_root = Path("/app")
    if (image_root / "server" / "alembic.ini").is_file():
        return image_root
    return candidate


SERVER_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = checkout_root()

if os.environ.get("LAMATHEK_ENV") == "dev":
    load_dotenv(REPO_ROOT / ".env.dev")
    load_dotenv(REPO_ROOT / ".env", override=True)
else:
    load_dotenv(REPO_ROOT / ".env")
load_dotenv(SERVER_ROOT / ".env", override=True)


def _sqlite_path() -> Path:
    raw = os.environ.get("SQLITE_PATH", "lamathek.sqlite3")
    path = Path(raw)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _database_url() -> str:
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit
    return f"sqlite:///{_sqlite_path()}"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_optional_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    DEBUG = _env_bool("FLASK_DEBUG", default=False)

    OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
    OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
    OIDC_SERVER_METADATA_URL = os.environ.get("OIDC_SERVER_METADATA_URL", "")
    OIDC_SCOPES = os.environ.get("OIDC_SCOPES", "openid profile email")
    OIDC_REDIRECT_URI = os.environ.get(
        "OIDC_REDIRECT_URI", "http://localhost:5173/auth/callback"
    )
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    AUTH_DEV_BYPASS = _env_bool("AUTH_DEV_BYPASS", default=False)
    AUTH_DEV_BYPASS_ALLOW = _env_bool("AUTH_DEV_BYPASS_ALLOW", default=False)
    AUTH_DEV_SUB = os.environ.get("AUTH_DEV_SUB", "")
    AUTH_DEV_NAME = os.environ.get("AUTH_DEV_NAME", "")
    AUTH_DEV_EMAIL = os.environ.get("AUTH_DEV_EMAIL", "")
    AUTH_DEV_SUPERUSER = _env_optional_bool("AUTH_DEV_SUPERUSER")
