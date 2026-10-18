"""ISO-3166-2:DE Kurzcodes für Kalender-Feiertage."""

DEFAULT_CALENDAR_BUNDESLAND = "HE"

CALENDAR_BUNDESLAND_CODES: frozenset[str] = frozenset(
    {
        "BW",
        "BY",
        "BE",
        "BB",
        "HB",
        "HH",
        "HE",
        "MV",
        "NI",
        "NW",
        "RP",
        "SL",
        "SN",
        "ST",
        "SH",
        "TH",
    }
)


def parse_calendar_bundesland(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_field")
    code = value.strip().upper()
    if code not in CALENDAR_BUNDESLAND_CODES:
        raise ValueError("invalid_calendar_bundesland")
    return code
