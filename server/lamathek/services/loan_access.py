from sqlalchemy.orm import Session

from lamathek.models.inventory import INVENTORY_VISIBILITY_ARCHIVED, Inventory
from lamathek.models.loan import LOAN_PHASE_DRAFT, Loan
from lamathek.models.user import User
from lamathek.services.inventories import (
    user_can_manage_inventory,
    user_can_view_inventory,
)


def user_is_borrower(user: User, loan: Loan) -> bool:
    return loan.borrower_user_id == user.id


def user_can_view_loan(session: Session, user: User, loan: Loan) -> bool:
    if user.is_superuser:
        return True
    if user_is_borrower(user, loan):
        return True
    if user_can_manage_inventory(session, user, loan.inventory):
        if loan.phase != LOAN_PHASE_DRAFT:
            return True
        return loan.contact_user_id == user.id
    return False


def user_can_create_loan_on_inventory(
    session: Session, user: User, inventory: Inventory
) -> bool:
    if inventory.visibility == INVENTORY_VISIBILITY_ARCHIVED:
        return False
    if user_can_manage_inventory(session, user, inventory):
        return True
    return user_can_view_inventory(session, user, inventory)
