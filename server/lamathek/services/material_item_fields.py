from datetime import date

from lamathek.models.material import (
    ITEM_STATUS_ACTIVE,
    Piece,
    StockLot,
    VALID_ITEM_STATUSES,
)

ACQUIRED_YEAR_MIN = 1900


def _max_acquired_year() -> int:
    return date.today().year + 1


def parse_acquired_year(value) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError("invalid_acquired_year")
    if value < ACQUIRED_YEAR_MIN or value > _max_acquired_year():
        raise ValueError("invalid_acquired_year")
    return value


def parse_new_value_cents(value) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError("invalid_new_value")
    if value < 0:
        raise ValueError("invalid_new_value")
    return value


def parse_item_status(value) -> str:
    if not isinstance(value, str) or value not in VALID_ITEM_STATUSES:
        raise ValueError("invalid_status")
    return value


def parse_optional_text(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_field")
    return value.strip() or None


def parse_optional_serial_number(value) -> str | None:
    parsed = parse_optional_text(value)
    if parsed is not None and len(parsed) > 255:
        raise ValueError("invalid_field")
    return parsed


def apply_item_fields_on_create(
    item: Piece | StockLot,
    *,
    acquired_year: int | None = None,
    note: str | None = None,
    source: str | None = None,
    serial_number: str | None = None,
    new_value_cents: int | None = None,
) -> None:
    item.acquired_year = acquired_year
    item.note = note
    item.source = source
    item.status = ITEM_STATUS_ACTIVE
    item.serial_number = serial_number
    item.new_value_cents = new_value_cents


def apply_item_field_updates(item: Piece | StockLot, body: dict) -> str | None:
    """Apply optional metadata from a PATCH/POST body. Keys use API camelCase.

    Returns requested status when present in body, else None.
    """
    if "acquiredYear" in body:
        item.acquired_year = parse_acquired_year(body.get("acquiredYear"))
    if "note" in body:
        item.note = parse_optional_text(body.get("note"))
    if "source" in body:
        item.source = parse_optional_text(body.get("source"))
    if "serialNumber" in body:
        item.serial_number = parse_optional_serial_number(body.get("serialNumber"))
    if "newValueCents" in body:
        item.new_value_cents = parse_new_value_cents(body.get("newValueCents"))
    if "status" in body:
        return parse_item_status(body.get("status"))
    return None


def parse_item_fields_for_create(body: dict) -> dict:
    result: dict = {}
    if "acquiredYear" in body and body.get("acquiredYear") is not None:
        result["acquired_year"] = parse_acquired_year(body.get("acquiredYear"))
    if "note" in body:
        result["note"] = parse_optional_text(body.get("note"))
    if "source" in body:
        result["source"] = parse_optional_text(body.get("source"))
    if "serialNumber" in body:
        result["serial_number"] = parse_optional_serial_number(body.get("serialNumber"))
    if "newValueCents" in body and body.get("newValueCents") is not None:
        result["new_value_cents"] = parse_new_value_cents(body.get("newValueCents"))
    return result
