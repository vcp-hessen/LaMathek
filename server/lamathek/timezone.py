"""IANA-Zeitzone der Instanz (env LAMATHEK_INSTANCE_TIMEZONE; PDFs, …)."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_INSTANCE_TIMEZONE = "Europe/Berlin"


def parse_instance_timezone(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_field")
    tz = value.strip()
    if not tz:
        raise ValueError("invalid_instance_timezone")
    try:
        ZoneInfo(tz)
    except Exception:
        raise ValueError("invalid_instance_timezone")
    return tz


def instance_zone() -> ZoneInfo:
    """Zone from the app config (LAMATHEK_INSTANCE_TIMEZONE), outside a request too."""
    from flask import current_app, has_app_context

    from lamathek.config import Config

    name = Config.INSTANCE_TIMEZONE
    if has_app_context():
        name = current_app.config.get("INSTANCE_TIMEZONE", name)
    return ZoneInfo(name)


def instance_now() -> datetime:
    """Wall clock of the instance, independent of the server's TZ."""
    return datetime.now(timezone.utc).astimezone(instance_zone())


def instance_today() -> date:
    """Calendar day of the instance; use instead of date.today()."""
    return instance_now().date()


def utc_iso(value: datetime | None) -> str | None:
    """ISO timestamp with offset for the API. SQLite returns naive UTC from func.now()."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
