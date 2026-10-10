"""Variant dimensions (Variantenbezeichner) on material types and selections on pieces/lots."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session, selectinload

from lamathek.models.material import (
    MaterialType,
    MaterialTypeVariant,
    MaterialTypeVariantValue,
    Piece,
    PieceVariantValue,
    StockLot,
    StockLotVariantValue,
)


def _validate_value_list(values: list) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, str):
            raise ValueError("invalid_variant_values")
        value = raw.strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def parse_variants_payload(raw) -> list[tuple[str, list[str]]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("invalid_variants")
    axes: list[tuple[str, list[str]]] = []
    labels_seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("invalid_variants")
        label_raw = entry.get("label")
        values_raw = entry.get("values")
        if not isinstance(label_raw, str) or not label_raw.strip():
            continue
        if values_raw is None:
            values_raw = []
        if not isinstance(values_raw, list):
            raise ValueError("invalid_variant_values")
        label = label_raw.strip()
        if label in labels_seen:
            raise ValueError("duplicate_variant_label")
        labels_seen.add(label)
        values = _validate_value_list(values_raw)
        if not values:
            continue
        axes.append((label, values))
    return axes


def ordered_variants(material_type: MaterialType) -> list[MaterialTypeVariant]:
    return list(material_type.variants)


def variant_axis_map(material_type: MaterialType) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for axis in ordered_variants(material_type):
        result[axis.label] = [v.value for v in axis.values]
    return result


def variants_to_json(material_type: MaterialType) -> list[dict]:
    return [
        {"label": axis.label, "values": [v.value for v in axis.values]}
        for axis in ordered_variants(material_type)
    ]


def _selection_map_from_piece(piece: Piece) -> dict[str, str]:
    by_variant_id = {sel.variant_id: sel for sel in piece.variant_selections}
    result: dict[str, str] = {}
    for axis in ordered_variants(piece.material_type):
        sel = by_variant_id.get(axis.id)
        if sel is not None:
            result[axis.label] = sel.value
    return result


def _selection_map_from_lot(lot: StockLot) -> dict[str, str]:
    by_variant_id = {sel.variant_id: sel for sel in lot.variant_selections}
    result: dict[str, str] = {}
    for axis in ordered_variants(lot.material_type):
        sel = by_variant_id.get(axis.id)
        if sel is not None:
            result[axis.label] = sel.value
    return result


def piece_variant_to_json(piece: Piece) -> dict[str, str]:
    return _selection_map_from_piece(piece)


def stock_lot_variant_to_json(lot: StockLot) -> dict[str, str]:
    return _selection_map_from_lot(lot)


def variant_summary_values(variant_map: dict[str, str], material_type: MaterialType) -> str:
    parts: list[str] = []
    for axis in ordered_variants(material_type):
        value = variant_map.get(axis.label)
        if value:
            parts.append(value)
    return " · ".join(parts)


def _parse_variant_body(raw, *, required_all: bool) -> dict[str, str | None]:
    if raw is None:
        if required_all:
            return {}
        return {}
    if not isinstance(raw, dict):
        raise ValueError("invalid_variant")
    parsed: dict[str, str | None] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("invalid_variant")
        label = key.strip()
        if value is None:
            parsed[label] = None
            continue
        if not isinstance(value, str):
            raise ValueError("invalid_variant")
        stripped = value.strip()
        parsed[label] = stripped if stripped else None
    return parsed


def validate_piece_variant_map(
    material_type: MaterialType, raw_variant
) -> dict[str, str]:
    axes = ordered_variants(material_type)
    if not axes:
        body = _parse_variant_body(raw_variant, required_all=False)
        if body:
            raise ValueError("variant_not_allowed")
        return {}

    body = _parse_variant_body(raw_variant, required_all=True)
    result: dict[str, str] = {}
    for axis in axes:
        chosen = body.get(axis.label)
        if chosen is None or not chosen:
            raise ValueError("variant_required")
        allowed = [v.value for v in axis.values]
        if chosen not in allowed:
            raise ValueError("invalid_variant")
        result[axis.label] = chosen
    for label in body:
        if label not in result:
            raise ValueError("invalid_variant")
    return result


def validate_lot_variant_map(
    material_type: MaterialType, raw_variant
) -> dict[str, str]:
    axes = ordered_variants(material_type)
    if not axes:
        body = _parse_variant_body(raw_variant, required_all=False)
        if body:
            raise ValueError("variant_not_allowed")
        return {}

    body = _parse_variant_body(raw_variant, required_all=False)
    result: dict[str, str] = {}
    for axis in axes:
        chosen = body.get(axis.label)
        if chosen is None or not chosen:
            continue
        allowed = [v.value for v in axis.values]
        if chosen not in allowed:
            raise ValueError("invalid_variant")
        result[axis.label] = chosen
    for label in body:
        if label not in {a.label for a in axes}:
            raise ValueError("invalid_variant")
    return result


def set_piece_variant_map(session: Session, piece: Piece, variant_map: dict[str, str]) -> None:
    session.execute(delete(PieceVariantValue).where(PieceVariantValue.piece_id == piece.id))
    piece.variant_selections.clear()
    label_to_axis = {axis.label: axis for axis in ordered_variants(piece.material_type)}
    for label, value in variant_map.items():
        axis = label_to_axis.get(label)
        if axis is None:
            continue
        session.add(
            PieceVariantValue(piece_id=piece.id, variant_id=axis.id, value=value)
        )


def set_lot_variant_map(session: Session, lot: StockLot, variant_map: dict[str, str]) -> None:
    session.execute(
        delete(StockLotVariantValue).where(StockLotVariantValue.stock_lot_id == lot.id)
    )
    lot.variant_selections.clear()
    label_to_axis = {axis.label: axis for axis in ordered_variants(lot.material_type)}
    for label, value in variant_map.items():
        axis = label_to_axis.get(label)
        if axis is None:
            continue
        session.add(
            StockLotVariantValue(stock_lot_id=lot.id, variant_id=axis.id, value=value)
        )


def replace_material_type_variants(
    session: Session,
    material_type: MaterialType,
    axes: list[tuple[str, list[str]]],
) -> None:
    piece_maps = [_selection_map_from_piece(piece) for piece in material_type.pieces]
    lot_maps = [_selection_map_from_lot(lot) for lot in material_type.stock_lots]

    session.execute(
        delete(MaterialTypeVariant).where(
            MaterialTypeVariant.material_type_id == material_type.id
        )
    )
    material_type.variants.clear()
    session.flush()

    for index, (label, values) in enumerate(axes):
        axis = MaterialTypeVariant(
            material_type_id=material_type.id,
            label=label,
            sort_order=index,
        )
        session.add(axis)
        session.flush()
        for v_index, value in enumerate(values):
            session.add(
                MaterialTypeVariantValue(
                    variant_id=axis.id,
                    sort_order=v_index,
                    value=value,
                )
            )
    session.flush()
    session.refresh(material_type)

    for piece, variant_map in zip(material_type.pieces, piece_maps, strict=True):
        set_piece_variant_map(session, piece, variant_map)
    for lot, variant_map in zip(material_type.stock_lots, lot_maps, strict=True):
        set_lot_variant_map(session, lot, variant_map)


def assert_variants_compatible_with_pieces(
    material_type: MaterialType, axes: list[tuple[str, list[str]]]
) -> None:
    new_map = {label: set(values) for label, values in axes}
    new_labels = set(new_map.keys())
    for piece in material_type.pieces:
        current = _selection_map_from_piece(piece)
        if not new_labels:
            if current:
                raise ValueError("variant_in_use")
            continue
        for label, value in current.items():
            if label not in new_labels:
                raise ValueError("variant_in_use")
            if value not in new_map[label]:
                raise ValueError("variant_in_use")


def assert_variants_compatible_with_lots(
    material_type: MaterialType, axes: list[tuple[str, list[str]]]
) -> None:
    new_map = {label: set(values) for label, values in axes}
    new_labels = set(new_map.keys())
    for lot in material_type.stock_lots:
        current = _selection_map_from_lot(lot)
        for label, value in current.items():
            if label not in new_labels or value not in new_map[label]:
                raise ValueError("variant_in_use")


def variant_load_options():
    return (
        selectinload(MaterialType.variants).selectinload(MaterialTypeVariant.values),
    )


def piece_variant_load_options():
    return (
        selectinload(Piece.variant_selections),
        selectinload(Piece.material_type).selectinload(MaterialType.variants).selectinload(
            MaterialTypeVariant.values
        ),
    )


def stock_lot_variant_load_options():
    return (
        selectinload(StockLot.variant_selections),
        selectinload(StockLot.material_type).selectinload(MaterialType.variants).selectinload(
            MaterialTypeVariant.values
        ),
    )
