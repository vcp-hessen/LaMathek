"""IANA-Zeitzone der Instanz (env LAMATHEK_INSTANCE_TIMEZONE; PDFs, …)."""

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
