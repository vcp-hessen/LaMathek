import os
from pathlib import Path

from dotenv import load_dotenv

from lamathek.timezone import DEFAULT_INSTANCE_TIMEZONE, parse_instance_timezone


def checkout_root() -> Path:
    """Repository root in a checkout; the working directory once pip-installed.

    Only used to find .env files and to resolve a relative SQLITE_PATH. The
    image sets SQLITE_PATH to an absolute path.
    """
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "server" / "pyproject.toml").is_file():
        return candidate
    return Path.cwd()


SERVER_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = checkout_root()

DEFAULT_SECRET_KEY = "dev-only-change-me"


def load_env_files() -> None:
    """Dev: .env.dev (tracked defaults) → .env.local (personal, gitignored) → .env.

    LAMATHEK_SKIP_DOTENV=1 skips all files so tests never pick up a developer's
    SMTP credentials or database path.
    """
    if os.environ.get("LAMATHEK_SKIP_DOTENV") == "1":
        return
    if os.environ.get("LAMATHEK_ENV") == "dev":
        load_dotenv(REPO_ROOT / ".env.dev")
        load_dotenv(REPO_ROOT / ".env.local", override=True)
        load_dotenv(REPO_ROOT / ".env", override=True)
    else:
        load_dotenv(REPO_ROOT / ".env")
    load_dotenv(SERVER_ROOT / ".env", override=True)


load_env_files()


def _sqlite_path() -> Path:
    raw = os.environ.get("SQLITE_PATH", "lamathek.sqlite3")
    path = Path(raw)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def media_path() -> Path:
    raw = os.environ.get("MEDIA_PATH")
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
    else:
        path = _sqlite_path().parent / "media"
    path.mkdir(parents=True, exist_ok=True)
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


def _instance_timezone_from_env() -> str:
    raw = os.environ.get("LAMATHEK_INSTANCE_TIMEZONE", DEFAULT_INSTANCE_TIMEZONE)
    return parse_instance_timezone(raw)


def _env_optional_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
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

    SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "").strip()
    SMTP_STARTTLS = _env_bool("SMTP_STARTTLS", default=True)
    SMTP_SSL = _env_bool("SMTP_SSL", default=False)
    SMTP_TIMEOUT = float(os.environ.get("SMTP_TIMEOUT", "15"))

    INSTANCE_TIMEZONE = _instance_timezone_from_env()

    # Background sender for the mail outbox; off in tests and for the seed script.
    MAIL_OUTBOX_WORKER = _env_bool("MAIL_OUTBOX_WORKER", default=True)

    # Validate every /api answer against its model (ADR 0021). Unset: on with
    # TESTING or DEBUG. The end-to-end tests switch it on under gunicorn.
    API_CONTRACT_CHECK = _env_optional_bool("API_CONTRACT_CHECK")
