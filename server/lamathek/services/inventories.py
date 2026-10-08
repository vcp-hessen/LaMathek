from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lamathek.models.inventory import Inventory, InventoryPermission
from lamathek.models.user import User

ROLE_MATERIALWART = "materialwart"
ROLE_VERANTWORTLICHE = "verantwortliche"
VALID_ROLES = frozenset({ROLE_MATERIALWART, ROLE_VERANTWORTLICHE})


def list_inventories_for_user(session: Session, user: User) -> list[Inventory]:
    if user.is_superuser:
        return list(session.scalars(select(Inventory).order_by(Inventory.name)).all())
    if user.role != ROLE_MATERIALWART:
        return []
    return list(
        session.scalars(
            select(Inventory)
            .join(InventoryPermission)
            .where(InventoryPermission.user_id == user.id)
            .order_by(Inventory.name)
        ).all()
    )


def inventory_by_id(session: Session, inventory_id: int) -> Inventory | None:
    return session.get(Inventory, inventory_id)


def user_can_manage_inventory(session: Session, user: User, inventory: Inventory) -> bool:
    if user.is_superuser:
        return True
    if user.role != ROLE_MATERIALWART:
        return False
    permission = session.scalar(
        select(InventoryPermission).where(
            InventoryPermission.user_id == user.id,
            InventoryPermission.inventory_id == inventory.id,
        )
    )
    return permission is not None


def create_inventory(session: Session, name: str) -> Inventory:
    inventory = Inventory(name=name.strip())
    session.add(inventory)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("name_taken") from None
    session.refresh(inventory)
    return inventory


def rename_inventory(session: Session, inventory: Inventory, name: str) -> Inventory:
    inventory.name = name.strip()
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


def replace_permissions(
    session: Session, inventory: Inventory, user_ids: list[int]
) -> list[int]:
    session.execute(
        delete(InventoryPermission).where(
            InventoryPermission.inventory_id == inventory.id
        )
    )
    for user_id in user_ids:
        session.add(InventoryPermission(user_id=user_id, inventory_id=inventory.id))
    session.commit()
    return permission_user_ids(session, inventory.id)
