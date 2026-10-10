from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from lamathek.models.inventory import Inventory
from lamathek.models.material import TRACKING_STOCK, MaterialType, Piece, Stock
from lamathek.models.set import (
    SET_ROLE_ASSIGNMENT,
    SET_ROLE_OPTIONAL,
    VALID_SET_ROLES,
    MaterialSet,
    SetStockLine,
)


def _load_set(session: Session, set_id: int) -> MaterialSet | None:
    return session.scalar(
        select(MaterialSet)
        .where(MaterialSet.id == set_id)
        .options(
            selectinload(MaterialSet.inventory),
            selectinload(MaterialSet.pieces).selectinload(Piece.material_type),
            selectinload(MaterialSet.stock_lines).selectinload(SetStockLine.material_type),
        )
    )


def set_by_id(session: Session, set_id: int) -> MaterialSet | None:
    return _load_set(session, set_id)


def list_sets(session: Session, inventory_id: int) -> list[MaterialSet]:
    return list(
        session.scalars(
            select(MaterialSet)
            .where(MaterialSet.inventory_id == inventory_id)
            .order_by(MaterialSet.name)
        ).all()
    )


def _normalize_short_name(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _integrity_set_error(exc: IntegrityError) -> ValueError:
    message = str(exc).lower()
    if "short_name" in message:
        return ValueError("short_name_taken")
    return ValueError("name_taken")


def create_set(
    session: Session,
    inventory: Inventory,
    name: str,
    *,
    short_name: str | None = None,
) -> MaterialSet:
    material_set = MaterialSet(
        inventory_id=inventory.id,
        name=name.strip(),
        short_name=_normalize_short_name(short_name),
    )
    session.add(material_set)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _integrity_set_error(exc) from None
    session.refresh(material_set)
    return _load_set(session, material_set.id)  # type: ignore[return-value]


def rename_set(session: Session, material_set: MaterialSet, name: str) -> MaterialSet:
    return update_set(session, material_set, name=name)


def update_set(
    session: Session,
    material_set: MaterialSet,
    *,
    name: str | None = None,
    short_name: str | None = None,
    short_name_sent: bool = False,
) -> MaterialSet:
    if name is not None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("invalid_name")
        material_set.name = name.strip()
    if short_name_sent:
        material_set.short_name = _normalize_short_name(short_name)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _integrity_set_error(exc) from None
    return _load_set(session, material_set.id)  # type: ignore[return-value]


def delete_set(session: Session, material_set: MaterialSet) -> None:
    from sqlalchemy import update

    from lamathek.models.loan import LoanLine

    session.execute(
        update(LoanLine)
        .where(LoanLine.origin_set_id == material_set.id)
        .values(
            origin_set_id=None,
            origin_set_name=None,
            origin_set_role=None,
        )
    )
    for piece in list(material_set.pieces):
        piece.set_id = None
        piece.set_role = None
    session.delete(material_set)
    session.commit()


def _stock_quantity(session: Session, material_type_id: int) -> int:
    row = session.scalar(
        select(Stock.quantity).where(Stock.material_type_id == material_type_id)
    )
    return int(row) if row is not None else 0


def _reserved_stock(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    *,
    exclude_line_id: int | None = None,
) -> int:
    stmt = (
        select(func.coalesce(func.sum(SetStockLine.quantity), 0))
        .join(MaterialSet)
        .where(
            MaterialSet.inventory_id == inventory_id,
            SetStockLine.material_type_id == material_type_id,
        )
    )
    if exclude_line_id is not None:
        stmt = stmt.where(SetStockLine.id != exclude_line_id)
    total = session.scalar(stmt)
    return int(total or 0)


def _validate_stock_reservation(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    new_quantity: int,
    *,
    exclude_line_id: int | None = None,
) -> None:
    available = _stock_quantity(session, material_type_id)
    reserved = _reserved_stock(
        session, inventory_id, material_type_id, exclude_line_id=exclude_line_id
    )
    if reserved + new_quantity > available:
        raise ValueError("over_reserved")


def set_piece_membership(
    session: Session,
    material_set: MaterialSet,
    piece_id: int,
    role: str | None,
) -> Piece:
    material_set = _load_set(session, material_set.id)
    if material_set is None:
        raise ValueError("not_found")

    piece = session.scalar(
        select(Piece)
        .where(Piece.id == piece_id)
        .options(
            selectinload(Piece.material_type).selectinload(MaterialType.inventory),
            selectinload(Piece.material_set),
        )
    )
    if piece is None:
        raise ValueError("not_found")
    if piece.material_type.inventory_id != material_set.inventory_id:
        raise ValueError("invalid_piece")

    if role is None:
        if piece.set_id == material_set.id:
            piece.set_id = None
            piece.set_role = None
        session.commit()
        return piece

    if role not in VALID_SET_ROLES:
        raise ValueError("invalid_role")
    if piece.set_id is not None and piece.set_id != material_set.id:
        raise ValueError("piece_on_other_set")

    piece.set_id = material_set.id
    piece.set_role = role
    session.commit()
    session.refresh(piece)
    return piece


def upsert_stock_line(
    session: Session,
    material_set: MaterialSet,
    material_type_id: int,
    role: str,
    quantity: int,
) -> SetStockLine | None:
    material_set = _load_set(session, material_set.id)
    if material_set is None:
        raise ValueError("not_found")

    if role not in VALID_SET_ROLES:
        raise ValueError("invalid_role")

    material_type = session.get(MaterialType, material_type_id)
    if material_type is None or material_type.inventory_id != material_set.inventory_id:
        raise ValueError("invalid_material_type")
    if material_type.tracking != TRACKING_STOCK:
        raise ValueError("not_stock_tracking")

    existing = session.scalar(
        select(SetStockLine).where(
            SetStockLine.set_id == material_set.id,
            SetStockLine.material_type_id == material_type_id,
            SetStockLine.role == role,
        )
    )

    if quantity <= 0:
        if existing is not None:
            session.delete(existing)
            session.commit()
        return None

    if existing is not None:
        _validate_stock_reservation(
            session,
            material_set.inventory_id,
            material_type_id,
            quantity,
            exclude_line_id=existing.id,
        )
        existing.quantity = quantity
        session.commit()
        session.refresh(existing)
        return existing

    _validate_stock_reservation(
        session,
        material_set.inventory_id,
        material_type_id,
        quantity,
    )
    line = SetStockLine(
        set_id=material_set.id,
        material_type_id=material_type_id,
        role=role,
        quantity=quantity,
    )
    session.add(line)
    session.commit()
    session.refresh(line)
    return line
