from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from lamathek.models.inventory import Inventory
from lamathek.services.categories import resolve_category_id
from lamathek.models.damage import Damage
from lamathek.models.material import (
    TRACKING_PIECE,
    TRACKING_STOCK,
    MaterialType,
    MaterialTypeVariantValue,
    Piece,
    Stock,
    VALID_TRACKING,
)


def _load_material_type(session: Session, material_type_id: int) -> MaterialType | None:
    return session.scalar(
        select(MaterialType)
        .where(MaterialType.id == material_type_id)
        .options(
            selectinload(MaterialType.variant_values),
            selectinload(MaterialType.pieces),
            selectinload(MaterialType.stock),
            selectinload(MaterialType.inventory),
            selectinload(MaterialType.category),
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
                selectinload(MaterialType.variant_values),
                selectinload(MaterialType.category),
            )
            .order_by(MaterialType.name)
        ).all()
    )


def _variant_value_strings(material_type: MaterialType) -> list[str]:
    return [v.value for v in material_type.variant_values]


def _material_type_has_usage(material_type: MaterialType) -> bool:
    if material_type.pieces:
        return True
    if material_type.stock is not None and material_type.stock.quantity > 0:
        return True
    if material_type.stock is not None:
        return True
    return False


def _validate_variant_values(values: list[str]) -> list[str]:
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


def _validate_piece_variant(material_type: MaterialType, variant: str | None) -> str | None:
    allowed = _variant_value_strings(material_type)
    if not allowed:
        if variant is not None and str(variant).strip():
            raise ValueError("variant_not_allowed")
        return None
    if variant is None or not str(variant).strip():
        raise ValueError("variant_required")
    chosen = str(variant).strip()
    if chosen not in allowed:
        raise ValueError("invalid_variant")
    return chosen


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
    variant_label: str | None,
    variant_values: list[str],
    *,
    short_name: str | None = None,
    description: str | None = None,
    unit: str | None = None,
    consumable: bool = False,
    category_id: int | None = None,
    category_name: str | None = None,
) -> MaterialType:
    if tracking not in VALID_TRACKING:
        raise ValueError("invalid_tracking")
    cleaned_values = _validate_variant_values(variant_values)
    label = variant_label.strip() if isinstance(variant_label, str) and variant_label.strip() else None
    if cleaned_values and not label:
        raise ValueError("variant_label_required")
    if label and not cleaned_values:
        label = None

    resolved_category_id = resolve_category_id(
        session, category_id=category_id, category_name=category_name
    )
    material_type = MaterialType(
        inventory_id=inventory.id,
        name=name.strip(),
        tracking=tracking,
        variant_label=label,
        short_name=_normalize_short_name(short_name),
        description=_normalize_optional_text(description),
        unit=_unit_for_tracking(tracking, unit),
        consumable=bool(consumable),
        category_id=resolved_category_id,
    )
    session.add(material_type)
    session.flush()
    for index, value in enumerate(cleaned_values):
        session.add(
            MaterialTypeVariantValue(
                material_type_id=material_type.id,
                sort_order=index,
                value=value,
            )
        )
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
    variant_label: str | None = None,
    variant_values: list[str] | None = None,
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

    if variant_values is not None or variant_label is not None:
        new_label = material_type.variant_label
        if variant_label is not None:
            new_label = (
                variant_label.strip()
                if isinstance(variant_label, str) and variant_label.strip()
                else None
            )
        new_values = (
            _validate_variant_values(variant_values)
            if variant_values is not None
            else _variant_value_strings(material_type)
        )
        if new_values and not new_label:
            raise ValueError("variant_label_required")
        if not new_values:
            new_label = None
        for piece in material_type.pieces:
            if new_values:
                if piece.variant not in new_values:
                    raise ValueError("variant_in_use")
            elif piece.variant:
                raise ValueError("variant_in_use")
        session.execute(
            delete(MaterialTypeVariantValue).where(
                MaterialTypeVariantValue.material_type_id == material_type.id
            )
        )
        material_type.variant_label = new_label
        for index, value in enumerate(new_values):
            session.add(
                MaterialTypeVariantValue(
                    material_type_id=material_type.id,
                    sort_order=index,
                    value=value,
                )
            )

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
                selectinload(Piece.material_type).selectinload(MaterialType.variant_values),
                selectinload(Piece.material_type).selectinload(MaterialType.inventory),
                selectinload(Piece.material_set),
            )
            .order_by(Piece.name)
        ).all()
    )


def piece_by_id(session: Session, piece_id: int) -> Piece | None:
    return session.scalar(
        select(Piece)
        .where(Piece.id == piece_id)
        .options(
            selectinload(Piece.material_type).selectinload(MaterialType.variant_values),
            selectinload(Piece.material_type).selectinload(MaterialType.inventory),
            selectinload(Piece.material_set),
            selectinload(Piece.damages).selectinload(Damage.repair),
        )
    )


MAX_PIECES_BATCH_COUNT = 24


def _piece_names_from_pattern(pattern: str, count: int) -> list[str]:
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("invalid_name_pattern")
    normalized = pattern.strip()
    if "{n}" not in normalized:
        raise ValueError("invalid_name_pattern")
    return [normalized.replace("{n}", str(n)) for n in range(1, count + 1)]


def _new_piece_row(
    material_type: MaterialType,
    name: str,
    variant: str | None,
) -> Piece:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("invalid_name")
    variant_value = _validate_piece_variant(material_type, variant)
    return Piece(
        material_type_id=material_type.id,
        name=name.strip(),
        variant=variant_value,
    )


def create_piece(
    session: Session,
    inventory: Inventory,
    material_type_id: int,
    name: str,
    variant: str | None,
) -> Piece:
    material_type = _load_material_type(session, material_type_id)
    if material_type is None or material_type.inventory_id != inventory.id:
        raise ValueError("invalid_material_type")
    if material_type.tracking != TRACKING_PIECE:
        raise ValueError("not_piece_tracking")
    piece = _new_piece_row(material_type, name, variant)
    session.add(piece)
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
    variant: str | None,
    set_id: int | None,
    set_name: str | None,
    set_short_name: str | None,
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
    variant_value = _validate_piece_variant(material_type, variant)

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
        for piece_name in names:
            piece = _new_piece_row(material_type, piece_name, variant_value)
            session.add(piece)
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
    variant: str | None = None,
) -> Piece:
    piece = piece_by_id(session, piece.id)
    if piece is None:
        raise ValueError("not_found")
    material_type = piece.material_type

    if material_type_id is not None and material_type_id != piece.material_type_id:
        new_type = _load_material_type(session, material_type_id)
        if new_type is None or new_type.inventory_id != material_type.inventory_id:
            raise ValueError("invalid_material_type")
        if new_type.tracking != TRACKING_PIECE:
            raise ValueError("not_piece_tracking")
        material_type = new_type
        piece.material_type_id = new_type.id
        piece.material_type = new_type

    if name is not None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("invalid_name")
        piece.name = name.strip()

    if material_type_id is not None:
        piece.variant = _validate_piece_variant(material_type, piece.variant)
    elif variant is not None:
        piece.variant = _validate_piece_variant(material_type, variant)

    session.commit()
    return piece_by_id(session, piece.id)  # type: ignore[return-value]


def delete_material_type(session: Session, material_type: MaterialType) -> None:
    session.delete(material_type)
    session.commit()


def delete_piece(session: Session, piece: Piece) -> None:
    from lamathek.services.loans import piece_on_open_loan

    if piece_on_open_loan(session, piece.id):
        raise ValueError("piece_on_loan")
    session.delete(piece)
    session.commit()


def list_stocks(session: Session, inventory_id: int) -> list[tuple[MaterialType, int]]:
    types = list(
        session.scalars(
            select(MaterialType)
            .where(
                MaterialType.inventory_id == inventory_id,
                MaterialType.tracking == TRACKING_STOCK,
            )
            .options(selectinload(MaterialType.stock))
            .order_by(MaterialType.name)
        ).all()
    )
    result: list[tuple[MaterialType, int]] = []
    for material_type in types:
        qty = material_type.stock.quantity if material_type.stock else 0
        result.append((material_type, qty))
    return result


def set_stock_quantity(
    session: Session,
    inventory: Inventory,
    material_type_id: int,
    quantity: int,
) -> tuple[MaterialType, int]:
    if not isinstance(quantity, int) or quantity < 0:
        raise ValueError("invalid_quantity")
    material_type = _load_material_type(session, material_type_id)
    if material_type is None or material_type.inventory_id != inventory.id:
        raise ValueError("invalid_material_type")
    if material_type.tracking != TRACKING_STOCK:
        raise ValueError("not_stock_tracking")
    from lamathek.services.loans import minimum_stock_quantity

    floor = minimum_stock_quantity(session, inventory.id, material_type_id)
    if quantity < floor:
        raise ValueError("below_loaned")
    if material_type.stock is None:
        material_type.stock = Stock(material_type_id=material_type.id, quantity=quantity)
        session.add(material_type.stock)
    else:
        material_type.stock.quantity = quantity
    session.commit()
    session.refresh(material_type)
    return material_type, quantity
