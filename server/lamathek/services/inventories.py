from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lamathek.models.inventory import Inventory, InventoryPermission
from lamathek.models.user import User

def list_inventories_for_user(session: Session, user: User) -> list[Inventory]:
    if user.is_superuser:
        return list(session.scalars(select(Inventory).order_by(Inventory.name)).all())
    return list(
        session.scalars(
            select(Inventory)
            .join(InventoryPermission)
            .where(InventoryPermission.user_id == user.id)
            .order_by(Inventory.name)
        ).all()
    )


def users_with_inventory_permission(session: Session) -> list[User]:
    user_ids = session.scalars(select(InventoryPermission.user_id).distinct()).all()
    if not user_ids:
        return []
    return list(
        session.scalars(
            select(User).where(User.id.in_(user_ids)).order_by(User.name, User.email)
        ).all()
    )


def format_content_responsible_users(users: list[User]) -> str:
    lines: list[str] = []
    for user in users:
        name = (user.name or "").strip()
        email = (user.email or "").strip()
        if name and email:
            lines.append(f"{name} ({email})")
        elif name:
            lines.append(name)
        elif email:
            lines.append(email)
    return "\n".join(lines)


def inventory_by_id(session: Session, inventory_id: int) -> Inventory | None:
    return session.get(Inventory, inventory_id)


def user_can_manage_any_inventory(session: Session, user: User) -> bool:
    if user.is_superuser:
        return True
    permission = session.scalar(
        select(InventoryPermission.id).where(InventoryPermission.user_id == user.id)
    )
    return permission is not None


def user_can_manage_inventory(session: Session, user: User, inventory: Inventory) -> bool:
    if user.is_superuser:
        return True
    permission = session.scalar(
        select(InventoryPermission).where(
            InventoryPermission.user_id == user.id,
            InventoryPermission.inventory_id == inventory.id,
        )
    )
    return permission is not None


def _apply_location_fields(
    inventory: Inventory,
    *,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
    notes: str | None,
) -> None:
    if (latitude is None) != (longitude is None):
        raise ValueError("invalid_coordinates")
    inventory.address = address
    inventory.latitude = latitude
    inventory.longitude = longitude
    inventory.notes = notes


def create_inventory(
    session: Session,
    name: str,
    *,
    address: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    notes: str | None = None,
) -> Inventory:
    inventory = Inventory(name=name.strip())
    _apply_location_fields(
        inventory,
        address=address,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
    )
    session.add(inventory)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("name_taken") from None
    session.refresh(inventory)
    return inventory


def update_inventory(
    session: Session,
    inventory: Inventory,
    name: str,
    *,
    address: str | None,
    latitude: float | None,
    longitude: float | None,
    notes: str | None,
) -> Inventory:
    inventory.name = name.strip()
    _apply_location_fields(
        inventory,
        address=address,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("name_taken") from None
    session.refresh(inventory)
    return inventory


def permission_user_ids(session: Session, inventory_id: int) -> list[int]:
    rows = session.scalars(
        select(InventoryPermission.user_id).where(
            InventoryPermission.inventory_id == inventory_id
        )
    ).all()
    return list(rows)


def permission_users(session: Session, inventory_id: int) -> list[User]:
    user_ids = permission_user_ids(session, inventory_id)
    if not user_ids:
        return []
    return list(
        session.scalars(
            select(User).where(User.id.in_(user_ids)).order_by(User.name, User.email)
        ).all()
    )


def delete_inventory(session: Session, inventory: Inventory) -> None:
    session.delete(inventory)
    session.commit()


def replace_permissions(
    session: Session, inventory: Inventory, user_ids: list[int]
) -> list[int]:
    from lamathek.services.users import count_superusers

    unique_ids: list[int] = []
    seen: set[int] = set()
    for user_id in user_ids:
        if user_id in seen:
            continue
        seen.add(user_id)
        unique_ids.append(user_id)

    if not unique_ids and count_superusers(session) == 0:
        raise ValueError("cannot_clear_permissions")

    if unique_ids:
        found = session.scalars(select(User.id).where(User.id.in_(unique_ids))).all()
        if len(found) != len(unique_ids):
            raise ValueError("invalid_user_ids")

    session.execute(
        delete(InventoryPermission).where(
            InventoryPermission.inventory_id == inventory.id
        )
    )
    for user_id in unique_ids:
        session.add(InventoryPermission(user_id=user_id, inventory_id=inventory.id))
    session.commit()
    return permission_user_ids(session, inventory.id)
