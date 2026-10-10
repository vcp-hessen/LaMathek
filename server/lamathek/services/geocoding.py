import json
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LaMathek/1.0 (material inventory; contact via installation)"


class GeocodingError(Exception):
    pass


def geocode_address(query: str) -> tuple[float, float]:
    trimmed = query.strip()
    if not trimmed:
        raise GeocodingError("empty_query")
    params = urllib.parse.urlencode(
        {
            "q": trimmed,
            "format": "json",
            "limit": "1",
            "countrycodes": "de",
        }
    )
    request = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise GeocodingError("upstream_failed") from None
    if not payload:
        raise GeocodingError("not_found")
    first = payload[0]
    try:
        latitude = float(first["lat"])
        longitude = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        raise GeocodingError("invalid_response") from None
    return latitude, longitude
