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


def user_can_edit_contact(session: Session, actor: User, target: User) -> bool:
    """Who may change a user's phone and email (mail and PDFs go to that address).

    Superusers anyone; login users only themselves (their IdP owns the email).
    A local user, who cannot sign in, may also be edited by a Materialwart*in of
    an Inventar where that user borrows, or by any Materialwart*in while the
    user has no Verleih yet (just created for a loan).
    """
    from sqlalchemy import select

    from lamathek.services.inventories import user_can_manage_any_inventory
    from lamathek.services.users import user_has_login

    if actor.is_superuser or actor.id == target.id:
        return True
    if user_has_login(target):
        return False
    inventories = session.scalars(
        select(Inventory).join(Loan, Loan.inventory_id == Inventory.id).where(
            Loan.borrower_user_id == target.id
        ).distinct()
    ).all()
    if not inventories:
        return user_can_manage_any_inventory(session, actor)
    return any(user_can_manage_inventory(session, actor, inv) for inv in inventories)
