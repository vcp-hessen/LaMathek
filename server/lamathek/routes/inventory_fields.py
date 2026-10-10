def optional_text(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_field")
    stripped = value.strip()
    return stripped if stripped else None


def optional_coordinates(body: dict) -> tuple[float | None, float | None]:
    latitude = body.get("latitude")
    longitude = body.get("longitude")
    if latitude is None and longitude is None:
        return None, None
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("invalid_coordinates")
    return float(latitude), float(longitude)


def inventory_location_from_body(body: dict) -> dict:
    latitude, longitude = optional_coordinates(body)
    return {
        "address": optional_text(body.get("address")),
        "latitude": latitude,
        "longitude": longitude,
        "notes": optional_text(body.get("notes")),
    }
