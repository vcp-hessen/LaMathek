from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lamathek.models.damage import Damage
from lamathek.models.inventory import Inventory
from lamathek.models.loan import Loan
from lamathek.models.material import MaterialType, Piece, StockLot
from lamathek.models.photo import Photo
from lamathek.models.set import MaterialSet
from lamathek.services.photo_storage import save_photo_variants


def photo_by_id(session: Session, photo_id: int) -> Photo | None:
    return session.get(Photo, photo_id)


def photos_to_json(photos: list[Photo]) -> list[dict]:
    ordered = sorted(photos, key=lambda p: (p.sort_order, p.id))
    return [{"id": p.id, "sortOrder": p.sort_order} for p in ordered]


def inventory_for_photo(session: Session, photo: Photo) -> Inventory | None:
    if photo.piece_id is not None:
        piece = session.get(Piece, photo.piece_id)
        if piece is None:
            return None
        return piece.material_type.inventory
    if photo.stock_lot_id is not None:
        lot = session.get(StockLot, photo.stock_lot_id)
        if lot is None:
            return None
        return lot.material_type.inventory
    if photo.set_id is not None:
        material_set = session.get(MaterialSet, photo.set_id)
        return material_set.inventory if material_set else None
    if photo.material_type_id is not None:
        material_type = session.get(MaterialType, photo.material_type_id)
        return material_type.inventory if material_type else None
    if photo.damage_id is not None:
        damage = session.get(Damage, photo.damage_id)
        if damage is None:
            return None
        return damage.piece.material_type.inventory
    if photo.inventory_id is not None:
        return session.get(Inventory, photo.inventory_id)
    if photo.loan_id is not None:
        loan = session.get(Loan, photo.loan_id)
        return loan.inventory if loan else None
    return None


def _next_sort_order(session: Session, query) -> int:
    current = session.scalar(select(func.max(Photo.sort_order)).where(query))
    return (current or 0) + 1


def add_photo(
    session: Session,
    *,
    raw_bytes: bytes,
    piece_id: int | None = None,
    stock_lot_id: int | None = None,
    set_id: int | None = None,
    material_type_id: int | None = None,
    damage_id: int | None = None,
    inventory_id: int | None = None,
    loan_id: int | None = None,
) -> Photo:
    owners = [
        piece_id,
        stock_lot_id,
        set_id,
        material_type_id,
        damage_id,
        inventory_id,
        loan_id,
    ]
    if sum(1 for value in owners if value is not None) != 1:
        raise ValueError("invalid_owner")

    photo = Photo(
        piece_id=piece_id,
        stock_lot_id=stock_lot_id,
        set_id=set_id,
        material_type_id=material_type_id,
        damage_id=damage_id,
        inventory_id=inventory_id,
        loan_id=loan_id,
        sort_order=0,
    )
    if piece_id is not None:
        photo.sort_order = _next_sort_order(session, Photo.piece_id == piece_id)
    elif stock_lot_id is not None:
        photo.sort_order = _next_sort_order(session, Photo.stock_lot_id == stock_lot_id)
    elif set_id is not None:
        photo.sort_order = _next_sort_order(session, Photo.set_id == set_id)
    elif material_type_id is not None:
        photo.sort_order = _next_sort_order(
            session, Photo.material_type_id == material_type_id
        )
    elif damage_id is not None:
        photo.sort_order = _next_sort_order(session, Photo.damage_id == damage_id)
    elif inventory_id is not None:
        photo.sort_order = _next_sort_order(session, Photo.inventory_id == inventory_id)
    elif loan_id is not None:
        photo.sort_order = _next_sort_order(session, Photo.loan_id == loan_id)

    session.add(photo)
    session.flush()

    try:
        save_photo_variants(photo.id, raw_bytes)
    except ValueError:
        session.delete(photo)
        session.flush()
        raise

    session.commit()
    session.refresh(photo)
    return photo


def delete_photo(session: Session, photo: Photo) -> None:
    session.delete(photo)
    session.commit()


def set_cover_photo(session: Session, photo: Photo) -> Photo:
    siblings_query = _sibling_filter(photo)
    if siblings_query is None:
        raise ValueError("invalid_owner")

    siblings = list(
        session.scalars(
            select(Photo).where(siblings_query).order_by(Photo.sort_order, Photo.id)
        ).all()
    )
    ordered = [photo] + [row for row in siblings if row.id != photo.id]
    for index, row in enumerate(ordered):
        row.sort_order = index
    session.commit()
    session.refresh(photo)
    return photo


def _sibling_filter(photo: Photo):
    if photo.piece_id is not None:
        return Photo.piece_id == photo.piece_id
    if photo.stock_lot_id is not None:
        return Photo.stock_lot_id == photo.stock_lot_id
    if photo.set_id is not None:
        return Photo.set_id == photo.set_id
    if photo.material_type_id is not None:
        return Photo.material_type_id == photo.material_type_id
    if photo.damage_id is not None:
        return Photo.damage_id == photo.damage_id
    if photo.inventory_id is not None:
        return Photo.inventory_id == photo.inventory_id
    if photo.loan_id is not None:
        return Photo.loan_id == photo.loan_id
    return None


def first_photo_ids_for_column(
    session: Session, column, owner_ids: list[int]
) -> dict[int, int]:
    if not owner_ids:
        return {}
    row_number = func.row_number().over(
        partition_by=column,
        order_by=(Photo.sort_order, Photo.id),
    )
    ranked = (
        select(
            column.label("owner_id"),
            Photo.id.label("photo_id"),
            row_number.label("rn"),
        )
        .where(column.in_(owner_ids))
        .subquery()
    )
    rows = session.execute(
        select(ranked.c.owner_id, ranked.c.photo_id).where(ranked.c.rn == 1)
    ).all()
    return {int(owner_id): int(photo_id) for owner_id, photo_id in rows}


def cover_photo_ids_for_pieces(session: Session, pieces: list[Piece]) -> dict[int, int | None]:
    if not pieces:
        return {}
    piece_ids = [p.id for p in pieces]
    material_type_ids = list({p.material_type_id for p in pieces})

    piece_photos = first_photo_ids_for_column(session, Photo.piece_id, piece_ids)
    type_photos = first_photo_ids_for_column(session, Photo.material_type_id, material_type_ids)

    return {
        piece.id: piece_photos.get(piece.id) or type_photos.get(piece.material_type_id)
        for piece in pieces
    }


def cover_photo_ids_for_stock_lots(
    session: Session, lots: list[StockLot]
) -> dict[int, int | None]:
    if not lots:
        return {}
    lot_ids = [lot.id for lot in lots]
    material_type_ids = list({lot.material_type_id for lot in lots})
    lot_photos = first_photo_ids_for_column(session, Photo.stock_lot_id, lot_ids)
    type_photos = first_photo_ids_for_column(session, Photo.material_type_id, material_type_ids)
    return {
        lot.id: lot_photos.get(lot.id) or type_photos.get(lot.material_type_id)
        for lot in lots
    }


def cover_photo_ids_for_material_types(
    session: Session, material_type_ids: list[int]
) -> dict[int, int | None]:
    found = first_photo_ids_for_column(session, Photo.material_type_id, material_type_ids)
    return {mt_id: found.get(mt_id) for mt_id in material_type_ids}


def cover_photo_ids_for_sets(session: Session, set_ids: list[int]) -> dict[int, int | None]:
    found = first_photo_ids_for_column(session, Photo.set_id, set_ids)
    return {set_id: found.get(set_id) for set_id in set_ids}


def cover_photo_id_for_inventory(session: Session, inventory_id: int) -> int | None:
    photo = session.scalar(
        select(Photo)
        .where(Photo.inventory_id == inventory_id)
        .order_by(Photo.sort_order, Photo.id)
        .limit(1)
    )
    return photo.id if photo else None


def cover_photo_ids_for_loans(session: Session, loan_ids: list[int]) -> dict[int, int | None]:
    found = first_photo_ids_for_column(session, Photo.loan_id, loan_ids)
    return {loan_id: found.get(loan_id) for loan_id in loan_ids}


def cover_photo_ids_for_inventories(
    session: Session, inventory_ids: list[int]
) -> dict[int, int | None]:
    found = first_photo_ids_for_column(session, Photo.inventory_id, inventory_ids)
    return {inventory_id: found.get(inventory_id) for inventory_id in inventory_ids}
