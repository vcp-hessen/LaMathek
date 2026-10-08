import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SERVER_ROOT = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit
    path = os.environ.get("SQLITE_PATH", str(SERVER_ROOT / "lamathek.sqlite3"))
    return f"sqlite:///{path}"


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
