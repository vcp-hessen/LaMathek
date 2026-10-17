from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from lamathek.models.inventory import Inventory
from lamathek.models.set import SetStockLine
from lamathek.services.categories import resolve_category_id
from lamathek.models.damage import Damage
from lamathek.models.material import (
    ITEM_STATUS_ACTIVE,
    ITEM_STATUS_RETIRED,
    TRACKING_PIECE,
    TRACKING_STOCK,
    MaterialType,
    Piece,
    StockLot,
    VALID_TRACKING,
)
from lamathek.services.material_item_fields import (
    apply_item_field_updates,
    apply_item_fields_on_create,
)
from lamathek.services.variants import (
    assert_variants_compatible_with_lots,
    assert_variants_compatible_with_pieces,
    parse_variants_payload,
    piece_variant_load_options,
    replace_material_type_variants,
    set_lot_variant_map,
    set_piece_variant_map,
    stock_lot_variant_load_options,
    validate_lot_variant_map,
    validate_piece_variant_map,
    variant_load_options,
)


def _load_material_type(session: Session, material_type_id: int) -> MaterialType | None:
    return session.scalar(
        select(MaterialType)
        .where(MaterialType.id == material_type_id)
        .options(
            *variant_load_options(),
            selectinload(MaterialType.pieces).selectinload(Piece.variant_selections),
            selectinload(MaterialType.stock_lots).selectinload(StockLot.variant_selections),
            selectinload(MaterialType.inventory),
            selectinload(MaterialType.category),
            selectinload(MaterialType.photos),
        )
    )


def material_type_by_id(session: Session, material_type_id: int) -> MaterialType | None:
    return _load_material_type(session, material_type_id)


def list_material_types(session: Session, inventory_id: int) -> list[MaterialType]:
    return list(
        session.scalars(
            select(MaterialType)
            .where(MaterialType.inventory_id == inventory_id)
            .options(
                *variant_load_options(),
                selectinload(MaterialType.category),
                selectinload(MaterialType.photos),
            )
            .order_by(MaterialType.name)
        ).all()
    )


def _material_type_has_usage(material_type: MaterialType) -> bool:
    if material_type.pieces:
        return True
    if material_type.stock_lots:
        return True
    return False


def material_type_usage_counts(
    session: Session, material_type_ids: list[int]
) -> dict[int, int]:
    if not material_type_ids:
        return {}
    counts: dict[int, int] = {tid: 0 for tid in material_type_ids}
    for material_type_id, total in session.execute(
        select(Piece.material_type_id, func.count())
        .where(Piece.material_type_id.in_(material_type_ids))
        .group_by(Piece.material_type_id)
    ).all():
        counts[material_type_id] = counts.get(material_type_id, 0) + int(total)
    for material_type_id, total in session.execute(
        select(StockLot.material_type_id, func.count())
        .where(StockLot.material_type_id.in_(material_type_ids))
        .group_by(StockLot.material_type_id)
    ).all():
        counts[material_type_id] = counts.get(material_type_id, 0) + int(total)
    for material_type_id, total in session.execute(
        select(SetStockLine.material_type_id, func.count())
        .where(SetStockLine.material_type_id.in_(material_type_ids))
        .group_by(SetStockLine.material_type_id)
    ).all():
        counts[material_type_id] = counts.get(material_type_id, 0) + int(total)
    return counts


def assert_material_type_empty(session: Session, material_type: MaterialType) -> None:
    material_type = _load_material_type(session, material_type.id)
    if material_type is None:
        raise ValueError("not_found")
    if _material_type_has_usage(material_type):
        raise ValueError("material_type_not_empty")
    set_lines = session.scalar(
        select(func.count())
        .select_from(SetStockLine)
        .where(SetStockLine.material_type_id == material_type.id)
    )
    if (set_lines or 0) > 0:
        raise ValueError("material_type_not_empty")


def _normalize_short_name(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _unit_for_tracking(tracking: str, unit: str | None) -> str | None:
    if tracking == TRACKING_PIECE:
        if unit is not None and str(unit).strip():
            raise ValueError("unit_not_for_piece")
        return None
    return _normalize_optional_text(unit)


def create_material_type(
    session: Session,
    inventory: Inventory,
    name: str,
    tracking: str,
    variants_payload,
    *,
    short_name: str | None = None,
    description: str | None = None,
    unit: str | None = None,
    consumable: bool = False,
    category_id: int | None = None,
    category_name: str | None = None,
    manufacturer: str | None = None,
    model_name: str | None = None,
) -> MaterialType:
    if tracking not in VALID_TRACKING:
        raise ValueError("invalid_tracking")
    axes = parse_variants_payload(variants_payload)

    resolved_category_id = resolve_category_id(
        session, category_id=category_id, category_name=category_name
    )
    material_type = MaterialType(
        inventory_id=inventory.id,
        name=name.strip(),
        tracking=tracking,
        short_name=_normalize_short_name(short_name),
        description=_normalize_optional_text(description),
        unit=_unit_for_tracking(tracking, unit),
        consumable=bool(consumable),
        category_id=resolved_category_id,
        manufacturer=_normalize_optional_text(manufacturer),
        model_name=_normalize_optional_text(model_name),
    )
    session.add(material_type)
    session.flush()
    replace_material_type_variants(session, material_type, axes)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if "short_name" in str(exc).lower():
            raise ValueError("short_name_taken") from None
        raise ValueError("name_taken") from None
    session.refresh(material_type)
    return _load_material_type(session, material_type.id)  # type: ignore[return-value]


def update_material_type(
    session: Session,
    material_type: MaterialType,
    *,
    name: str | None = None,
    tracking: str | None = None,
    variants_payload=None,
    short_name: str | None = None,
    description: str | None = None,
    unit: str | None = None,
    consumable: bool | None = None,
    category_id: int | None = None,
    category_name: str | None = None,
    clear_category: bool = False,
    short_name_sent: bool = False,
    description_sent: bool = False,
    unit_sent: bool = False,
    manufacturer_sent: bool = False,
    manufacturer: str | None = None,
    model_name_sent: bool = False,
    model_name: str | None = None,
) -> MaterialType:
    material_type = _load_material_type(session, material_type.id)
    if material_type is None:
        raise ValueError("not_found")

    if tracking is not None and tracking != material_type.tracking:
        if _material_type_has_usage(material_type):
            raise ValueError("tracking_locked")
        if tracking not in VALID_TRACKING:
            raise ValueError("invalid_tracking")
        material_type.tracking = tracking
        if tracking == TRACKING_PIECE:
            material_type.unit = None

    if name is not None:
        material_type.name = name.strip()

    if short_name_sent:
        material_type.short_name = _normalize_short_name(short_name)
    if description_sent:
        material_type.description = _normalize_optional_text(description)
    if unit_sent:
        material_type.unit = _unit_for_tracking(material_type.tracking, unit)
    if consumable is not None:
        material_type.consumable = bool(consumable)
    if clear_category or category_id is not None or category_name is not None:
        material_type.category_id = resolve_category_id(
            session,
            category_id=category_id,
            category_name=category_name,
            clear=clear_category,
        )

    if manufacturer_sent:
        material_type.manufacturer = _normalize_optional_text(manufacturer)
    if model_name_sent:
        material_type.model_name = _normalize_optional_text(model_name)

    if variants_payload is not None:
        axes = parse_variants_payload(variants_payload)
        assert_variants_compatible_with_pieces(material_type, axes)
        assert_variants_compatible_with_lots(material_type, axes)
        replace_material_type_variants(session, material_type, axes)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if "short_name" in str(exc).lower():
            raise ValueError("short_name_taken") from None
        raise ValueError("name_taken") from None
    return _load_material_type(session, material_type.id)  # type: ignore[return-value]


def list_pieces(session: Session, inventory_id: int) -> list[Piece]:
    return list(
        session.scalars(
            select(Piece)
            .join(MaterialType)
            .where(MaterialType.inventory_id == inventory_id)
            .options(
                *piece_variant_load_options(),
                selectinload(Piece.material_type).selectinload(MaterialType.inventory),
                selectinload(Piece.material_set),
                selectinload(Piece.photos),
            )
            .order_by(Piece.name)
        ).all()
    )


def piece_by_id(session: Session, piece_id: int) -> Piece | None:
    return session.scalar(
        select(Piece)
        .where(Piece.id == piece_id)
        .options(
            *piece_variant_load_options(),
            selectinload(Piece.material_type).selectinload(MaterialType.inventory),
            selectinload(Piece.material_set),
            selectinload(Piece.damages).selectinload(Damage.repair),
            selectinload(Piece.damages).selectinload(Damage.photos),
            selectinload(Piece.photos),
        )
    )


MAX_PIECES_BATCH_COUNT = 24


_BATCH_NAME_PLACEHOLDERS = ("{n}", "{a}", "{A}", "{r}", "{R}")


def _active_batch_placeholder(pattern: str) -> str | None:
    found = [token for token in _BATCH_NAME_PLACEHOLDERS if token in pattern]
    if len(found) != 1:
        return None
    return found[0]


def _int_to_roman_lower(num: int) -> str:
    if num < 1 or num > 3999:
        raise ValueError("invalid_name_pattern")
    values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    symbols = ["m", "cm", "d", "cd", "c", "xc", "l", "xl", "x", "ix", "v", "iv", "i"]
    result: list[str] = []
    n = num
    for value, symbol in zip(values, symbols, strict=True):
        while n >= value:
            result.append(symbol)
            n -= value
    return "".join(result)


def _piece_value_for_batch_placeholder(token: str, index: int) -> str:
    if token == "{n}":
        return str(index)
    if token == "{a}":
        if index < 1 or index > 26:
            raise ValueError("invalid_name_pattern")
        return chr(ord("a") + index - 1)
    if token == "{A}":
        if index < 1 or index > 26:
            raise ValueError("invalid_name_pattern")
        return chr(ord("A") + index - 1)
    if token == "{r}":
        return _int_to_roman_lower(index)
    if token == "{R}":
        return _int_to_roman_lower(index).upper()
    raise ValueError("invalid_name_pattern")


def _piece_names_from_pattern(pattern: str, count: int) -> list[str]:
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("invalid_name_pattern")
    normalized = pattern.strip()
    token = _active_batch_placeholder(normalized)
    if token is None or normalized.count(token) != 1:
        raise ValueError("invalid_name_pattern")
    names: list[str] = []
    for index in range(1, count + 1):
        names.append(normalized.replace(token, _piece_value_for_batch_placeholder(token, index)))
    return names


def _new_piece_row(
    session: Session,
    material_type: MaterialType,
    name: str,
    variant,
    *,
    item_fields: dict | None = None,
) -> Piece:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("invalid_name")
    variant_map = validate_piece_variant_map(material_type, variant)
    piece = Piece(
        material_type_id=material_type.id,
        name=name.strip(),
    )
    session.add(piece)
    session.flush()
    set_piece_variant_map(session, piece, variant_map)
    if item_fields:
        apply_item_fields_on_create(piece, **item_fields)
    return piece


def create_piece(
    session: Session,
    inventory: Inventory,
    material_type_id: int,
    name: str,
    variant,
    *,
    item_fields: dict | None = None,
) -> Piece:
    material_type = _load_material_type(session, material_type_id)
    if material_type is None or material_type.inventory_id != inventory.id:
        raise ValueError("invalid_material_type")
    if material_type.tracking != TRACKING_PIECE:
        raise ValueError("not_piece_tracking")
    fields = item_fields or {}
    piece = _new_piece_row(session, material_type, name, variant, item_fields=fields)
    session.commit()
    session.refresh(piece)
    return piece_by_id(session, piece.id)  # type: ignore[return-value]


def create_pieces_batch(
    session: Session,
    inventory: Inventory,
    *,
    material_type_id: int,
    count: int,
    name_pattern: str,
    variant,
    set_id: int | None,
    set_name: str | None,
    set_short_name: str | None,
    item_fields: dict | None = None,
) -> tuple[list[Piece], int | None]:
    from sqlalchemy.exc import IntegrityError

    from lamathek.models.set import SET_ROLE_ASSIGNMENT, MaterialSet
    from lamathek.services.sets import _normalize_short_name, set_by_id

    if not isinstance(count, int) or count < 1 or count > MAX_PIECES_BATCH_COUNT:
        raise ValueError("invalid_count")

    has_set_id = set_id is not None
    set_name_stripped = set_name.strip() if isinstance(set_name, str) and set_name.strip() else None
    if has_set_id and set_name_stripped:
        raise ValueError("set_conflict")

    material_type = _load_material_type(session, material_type_id)
    if material_type is None or material_type.inventory_id != inventory.id:
        raise ValueError("invalid_material_type")
    if material_type.tracking != TRACKING_PIECE:
        raise ValueError("not_piece_tracking")

    names = _piece_names_from_pattern(name_pattern, count)
    variant_map = validate_piece_variant_map(material_type, variant)

    material_set: MaterialSet | None = None
    if has_set_id:
        material_set = set_by_id(session, set_id)
        if material_set is None or material_set.inventory_id != inventory.id:
            raise ValueError("invalid_set")
    elif set_name_stripped:
        material_set = MaterialSet(
            inventory_id=inventory.id,
            name=set_name_stripped,
            short_name=_normalize_short_name(set_short_name),
        )
        session.add(material_set)

    created: list[Piece] = []
    try:
        fields = item_fields or {}
        for piece_name in names:
            piece = Piece(material_type_id=material_type.id, name=piece_name.strip())
            session.add(piece)
            session.flush()
            set_piece_variant_map(session, piece, variant_map)
            if fields:
                apply_item_fields_on_create(piece, **fields)
            created.append(piece)
        session.flush()

        if material_set is not None:
            for piece in created:
                piece.set_id = material_set.id
                piece.set_role = SET_ROLE_ASSIGNMENT

        session.commit()
    except IntegrityError as exc:
        session.rollback()
        message = str(exc).lower()
        if "short_name" in message:
            raise ValueError("short_name_taken") from None
        if "sets" in message or "name" in message:
            raise ValueError("name_taken") from None
        raise

    result_set_id = material_set.id if material_set is not None else None
    loaded = [
        piece_by_id(session, piece.id)  # type: ignore[misc]
        for piece in created
    ]
    return [p for p in loaded if p is not None], result_set_id


def update_piece(
    session: Session,
    piece: Piece,
    *,
    name: str | None = None,
    material_type_id: int | None = None,
    variant=None,
    metadata_body: dict | None = None,
) -> Piece:
    piece = piece_by_id(session, piece.id)
    if piece is None:
        raise ValueError("not_found")
    if material_type_id is not None and material_type_id != piece.material_type_id:
        raise ValueError("material_type_locked")
    material_type = piece.material_type

    if name is not None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("invalid_name")
        piece.name = name.strip()

    if variant is not None:
        variant_map = validate_piece_variant_map(material_type, variant)
        set_piece_variant_map(session, piece, variant_map)

    if metadata_body:
        new_status = apply_item_field_updates(piece, metadata_body)
        if new_status is not None:
            piece.status = new_status

    session.commit()
    return piece_by_id(session, piece.id)  # type: ignore[return-value]


def delete_material_type(session: Session, material_type: MaterialType) -> None:
    assert_material_type_empty(session, material_type)
    session.delete(material_type)
    session.commit()


def delete_piece(session: Session, piece: Piece) -> None:
    from lamathek.services.loans import piece_on_open_loan

    if piece_on_open_loan(session, piece.id):
        raise ValueError("piece_on_loan")
    session.delete(piece)
    session.commit()


def total_stock_quantity(session: Session, material_type_id: int) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(StockLot.quantity), 0)).where(
            StockLot.material_type_id == material_type_id,
            StockLot.status == ITEM_STATUS_ACTIVE,
        )
    )
    return int(total or 0)


def assert_can_retire_stock_lot(
    session: Session, lot: StockLot, inventory_id: int
) -> None:
    if lot.status != ITEM_STATUS_ACTIVE:
        return
    from lamathek.services.loans import minimum_stock_quantity

    floor = minimum_stock_quantity(session, inventory_id, lot.material_type_id)
    active_total = total_stock_quantity(session, lot.material_type_id)
    if active_total - lot.quantity < floor:
        raise ValueError("below_loaned")


def _stock_material_type(
    session: Session, inventory: Inventory, material_type_id: int
) -> MaterialType:
    material_type = _load_material_type(session, material_type_id)
    if material_type is None or material_type.inventory_id != inventory.id:
        raise ValueError("invalid_material_type")
    if material_type.tracking != TRACKING_STOCK:
        raise ValueError("not_stock_tracking")
    return material_type


def _assert_stock_floor(session: Session, inventory_id: int, material_type_id: int) -> None:
    from lamathek.services.loans import minimum_stock_quantity

    floor = minimum_stock_quantity(session, inventory_id, material_type_id)
    if total_stock_quantity(session, material_type_id) < floor:
        raise ValueError("below_loaned")


def list_stocks(session: Session, inventory_id: int) -> list[MaterialType]:
    return list(
        session.scalars(
            select(MaterialType)
            .where(
                MaterialType.inventory_id == inventory_id,
                MaterialType.tracking == TRACKING_STOCK,
            )
            .options(
                selectinload(MaterialType.stock_lots).selectinload(StockLot.variant_selections),
                selectinload(MaterialType.stock_lots).selectinload(StockLot.photos),
                *variant_load_options(),
            )
            .order_by(MaterialType.name)
        ).all()
    )


def stock_lot_by_id(session: Session, lot_id: int) -> StockLot | None:
    return session.scalar(
        select(StockLot)
        .where(StockLot.id == lot_id)
        .options(
            *stock_lot_variant_load_options(),
            selectinload(StockLot.material_type).selectinload(MaterialType.stock_lots),
        )
    )


def create_stock_lot(
    session: Session,
    inventory: Inventory,
    material_type_id: int,
    *,
    label: str | None,
    variant,
    quantity: int,
    item_fields: dict | None = None,
) -> MaterialType:
    if not isinstance(quantity, int) or quantity < 0:
        raise ValueError("invalid_quantity")
    material_type = _stock_material_type(session, inventory, material_type_id)
    variant_map = validate_lot_variant_map(material_type, variant)
    if quantity > 0:
        lot = StockLot(
            material_type_id=material_type.id,
            label=_normalize_optional_text(label),
            quantity=quantity,
        )
        session.add(lot)
        session.flush()
        set_lot_variant_map(session, lot, variant_map)
        if item_fields:
            apply_item_fields_on_create(lot, **item_fields)
        session.flush()
    _assert_stock_floor(session, inventory.id, material_type.id)
    session.commit()
    return _stock_material_type(session, inventory, material_type.id)


def update_stock_lot(
    session: Session,
    inventory: Inventory,
    lot: StockLot,
    *,
    label: str | None,
    variant,
    quantity: int,
    label_sent: bool,
    variant_sent: bool,
    metadata_body: dict | None = None,
) -> MaterialType:
    if not isinstance(quantity, int) or quantity < 0:
        raise ValueError("invalid_quantity")
    material_type = _stock_material_type(session, inventory, lot.material_type_id)
    if lot.material_type_id != material_type.id:
        raise ValueError("not_found")
    if label_sent:
        lot.label = _normalize_optional_text(label)
    if variant_sent:
        variant_map = validate_lot_variant_map(material_type, variant)
        set_lot_variant_map(session, lot, variant_map)
    if metadata_body:
        new_status = apply_item_field_updates(lot, metadata_body)
        if new_status is not None:
            if (
                new_status == ITEM_STATUS_RETIRED
                and lot.status == ITEM_STATUS_ACTIVE
            ):
                assert_can_retire_stock_lot(session, lot, inventory.id)
            lot.status = new_status

    lot.quantity = quantity
    session.flush()
    if lot.quantity == 0:
        session.delete(lot)
        session.flush()
    _assert_stock_floor(session, inventory.id, material_type.id)
    session.commit()
    return _stock_material_type(session, inventory, material_type.id)


def delete_stock_lot(session: Session, inventory: Inventory, lot: StockLot) -> MaterialType:
    material_type = _stock_material_type(session, inventory, lot.material_type_id)
    session.delete(lot)
    session.flush()
    _assert_stock_floor(session, inventory.id, material_type.id)
    session.commit()
    return _stock_material_type(session, inventory, material_type.id)


def apply_stock_loss(session: Session, material_type_id: int, quantity: int) -> None:
    if quantity <= 0:
        raise ValueError("invalid_quantity")
    lots = list(
        session.scalars(
            select(StockLot)
            .where(StockLot.material_type_id == material_type_id)
            .order_by(StockLot.id)
        ).all()
    )
    remaining = quantity
    for lot in lots:
        if remaining <= 0:
            break
        if lot.status != ITEM_STATUS_ACTIVE:
            continue
        take = min(lot.quantity, remaining)
        lot.quantity -= take
        remaining -= take
        if lot.quantity == 0:
            session.delete(lot)
    if remaining > 0:
        raise ValueError("invalid_loss")
