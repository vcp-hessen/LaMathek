from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from lamathek.models.inventory import Inventory
from lamathek.models.loan import (
    LINE_STATUS_DRAFT,
    LINE_STATUS_NOT_RETURNED,
    LINE_STATUS_REQUESTED,
    LINE_STATUS_WITHDRAWN,
    LINE_STATUSES_BLOCKING,
    LOAN_KIND_PERMANENT,
    LOAN_KIND_SHORT,
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_DRAFT,
    LOAN_PHASE_PACK,
    LOAN_PHASE_REVIEW,
    ORIGIN_SET_ROLE_ASSIGNMENT,
    ORIGIN_SET_ROLE_OPTIONAL,
    VALID_LOAN_KINDS,
    Event,
    Group,
    Loan,
    LoanLine,
)
from lamathek.models.material import ITEM_STATUS_RETIRED, Piece
from lamathek.models.set import (
    SET_ROLE_ASSIGNMENT,
    SET_ROLE_OPTIONAL,
    MaterialSet,
    SetStockLine,
)
from lamathek.models.user import User
from lamathek.services.piece_availability import (
    piece_has_open_severe_damage,
    piece_ids_with_open_total_loss,
    piece_is_blocked_for_lending,
)
from lamathek.services.inventories import user_can_manage_inventory
from lamathek.services.loan_workflow_steps import assert_line_action_allowed
def new_line_status_for_loan(loan: Loan) -> str:
    if loan.phase == LOAN_PHASE_DRAFT:
        return LINE_STATUS_DRAFT
    return LINE_STATUS_REQUESTED


def piece_blocked_on_loan(
    session: Session, piece_id: int, *, exclude_loan_id: int | None = None
) -> bool:
    stmt = select(LoanLine).join(Loan).where(LoanLine.piece_id == piece_id)
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    for line in session.scalars(stmt).all():
        if line.status in LINE_STATUSES_BLOCKING:
            return True
    return False
from lamathek.services.sets import set_by_id as load_set_by_id


def _loan_query():
    return select(Loan).options(
        selectinload(Loan.inventory),
        selectinload(Loan.group),
        selectinload(Loan.event),
        selectinload(Loan.borrower_user),
        selectinload(Loan.contact_user),
        selectinload(Loan.lines).selectinload(LoanLine.piece).selectinload(Piece.material_type),
        selectinload(Loan.lines).selectinload(LoanLine.material_type),
        selectinload(Loan.photos),
    )


def loan_by_id(session: Session, loan_id: int) -> Loan | None:
    return session.scalar(_loan_query().where(Loan.id == loan_id))


def list_loans(session: Session, inventory_id: int) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(Loan.inventory_id == inventory_id)
            .order_by(Loan.id.desc())
        ).all()
    )


def list_loans_for_manager(
    session: Session, inventory_id: int, *, viewer_user_id: int | None = None
) -> list[Loan]:
    visible = Loan.phase != LOAN_PHASE_DRAFT
    if viewer_user_id is not None:
        visible = or_(
            visible,
            Loan.borrower_user_id == viewer_user_id,
            Loan.contact_user_id == viewer_user_id,
        )
    return list(
        session.scalars(
            _loan_query()
            .where(Loan.inventory_id == inventory_id, visible)
            .order_by(Loan.id.desc())
        ).all()
    )


def list_loans_for_borrower(
    session: Session, inventory_id: int, borrower_user_id: int
) -> list[Loan]:
    return list(
        session.scalars(
            _loan_query()
            .where(
                Loan.inventory_id == inventory_id,
                Loan.borrower_user_id == borrower_user_id,
            )
            .order_by(Loan.id.desc())
        ).all()
    )


def list_loans_for_user_as_borrower(session: Session, user: User) -> list[Loan]:
    loans = list(
        session.scalars(
            _loan_query()
            .where(Loan.borrower_user_id == user.id)
            .order_by(Loan.id.desc())
        ).all()
    )
    return [loan for loan in loans if loan.inventory is not None]


def get_draft_loan(
    session: Session, inventory_id: int, borrower_user_id: int
) -> Loan | None:
    return session.scalar(
        _loan_query()
        .where(
            Loan.inventory_id == inventory_id,
            Loan.borrower_user_id == borrower_user_id,
            Loan.phase == LOAN_PHASE_DRAFT,
        )
        .order_by(Loan.id.desc())
        .limit(1)
    )


def list_groups(session: Session) -> list[Group]:
    return list(session.scalars(select(Group).order_by(Group.name)).all())


def list_events(session: Session) -> list[Event]:
    return list(session.scalars(select(Event).order_by(Event.name)).all())


def get_or_create_group(session: Session, name: str) -> Group:
    trimmed = name.strip()
    group = session.scalar(select(Group).where(Group.name == trimmed))
    if group is not None:
        return group
    group = Group(name=trimmed)
    session.add(group)
    session.flush()
    return group


def get_or_create_event(session: Session, name: str) -> Event:
    trimmed = name.strip()
    event = session.scalar(select(Event).where(Event.name == trimmed))
    if event is not None:
        return event
    event = Event(name=trimmed)
    session.add(event)
    session.flush()
    return event


def _validate_borrower(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("invalid_borrower")
    return user


def create_loan(
    session: Session,
    inventory: Inventory,
    *,
    group_name: str,
    borrower_user_id: int,
    event_name: str | None,
    pickup_on: date | None,
    return_on: date | None,
    kind: str = LOAN_KIND_SHORT,
    actor: User | None = None,
) -> Loan:
    if kind not in VALID_LOAN_KINDS:
        raise ValueError("invalid_kind")
    _validate_borrower(session, borrower_user_id)
    for_other = actor is not None and actor.id != borrower_user_id
    if kind == LOAN_KIND_PERMANENT:
        if (
            (event_name is not None and event_name.strip())
            or return_on is not None
        ):
            raise ValueError("invalid_permanent_fields")
        event_name = None
        return_on = None
    elif pickup_on is not None and return_on is not None and return_on < pickup_on:
        raise ValueError("invalid_date_range")
    group = get_or_create_group(session, group_name)
    event = None
    if event_name is not None and event_name.strip():
        event = get_or_create_event(session, event_name)
    loan = Loan(
        inventory_id=inventory.id,
        group_id=group.id,
        borrower_user_id=borrower_user_id,
        contact_user_id=actor.id if for_other and actor is not None else None,
        event_id=event.id if event else None,
        phase=LOAN_PHASE_DRAFT,
        kind=kind,
        wish_pickup_on=pickup_on,
        wish_return_on=return_on,
        pickup_on=pickup_on if for_other else None,
        return_on=return_on if for_other else None,
    )
    session.add(loan)
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def get_or_create_draft_loan(
    session: Session,
    inventory: Inventory,
    borrower_user_id: int,
    *,
    group_name: str = "—",
) -> Loan:
    draft = get_draft_loan(session, inventory.id, borrower_user_id)
    if draft is not None:
        return draft
    return create_loan(
        session,
        inventory,
        group_name=group_name,
        borrower_user_id=borrower_user_id,
        event_name=None,
        pickup_on=None,
        return_on=None,
    )


def update_loan(
    session: Session,
    loan: Loan,
    *,
    actor: User | None = None,
    group_name: str | None = None,
    borrower_user_id: int | None = None,
    event_name: str | None = None,
    clear_event: bool = False,
    wish_pickup_on: date | None = None,
    wish_return_on: date | None = None,
    update_wish_pickup_on: bool = False,
    update_wish_return_on: bool = False,
    pickup_on: date | None = None,
    return_on: date | None = None,
    update_pickup_on: bool = False,
    update_return_on: bool = False,
    kind: str | None = None,
    contact_user_id: int | None = None,
    update_contact: bool = False,
    pickup_note: str | None = None,
    update_pickup_note: bool = False,
    return_note: str | None = None,
    update_return_note: bool = False,
    manager_edit: bool = False,
    allow_shared_meta: bool = False,
) -> Loan:
    updated_fields: list[str] = []
    if loan.phase == LOAN_PHASE_CLOSED:
        raise ValueError("loan_not_editable")
    if loan.phase != LOAN_PHASE_DRAFT:
        if borrower_user_id is not None:
            raise ValueError("invalid_loan_state")
        if not manager_edit:
            if kind is not None:
                raise ValueError("invalid_loan_state")
            if group_name is not None:
                raise ValueError("invalid_loan_state")
            if clear_event:
                raise ValueError("invalid_loan_state")
            if event_name is not None and event_name.strip():
                raise ValueError("invalid_loan_state")
    if kind is not None:
        if kind not in VALID_LOAN_KINDS:
            raise ValueError("invalid_kind")
        loan.kind = kind
        updated_fields.append("kind")
        if kind == LOAN_KIND_PERMANENT:
            loan.event_id = None
            loan.return_on = None
    effective_kind = loan.kind
    if effective_kind == LOAN_KIND_PERMANENT:
        if event_name is not None and event_name.strip():
            raise ValueError("invalid_permanent_fields")
        if update_return_on and return_on is not None:
            raise ValueError("invalid_permanent_fields")
    if update_wish_pickup_on or update_wish_return_on:
        new_wish_pickup = wish_pickup_on if update_wish_pickup_on else loan.wish_pickup_on
        new_wish_return = wish_return_on if update_wish_return_on else loan.wish_return_on
        if (
            effective_kind != LOAN_KIND_PERMANENT
            and new_wish_pickup is not None
            and new_wish_return is not None
            and new_wish_return < new_wish_pickup
        ):
            raise ValueError("invalid_date_range")
    if update_pickup_on or update_return_on:
        new_pickup = pickup_on if update_pickup_on else loan.pickup_on
        new_return = return_on if update_return_on else loan.return_on
        if (
            effective_kind != LOAN_KIND_PERMANENT
            and new_pickup is not None
            and new_return is not None
            and new_return < new_pickup
        ):
            raise ValueError("invalid_date_range")
    meta_editable = allow_shared_meta or manager_edit
    if group_name is not None and meta_editable:
        loan.group = get_or_create_group(session, group_name)
        updated_fields.append("group")
    if borrower_user_id is not None and meta_editable:
        _validate_borrower(session, borrower_user_id)
        loan.borrower_user_id = borrower_user_id
        updated_fields.append("borrower")
    if clear_event and meta_editable:
        loan.event_id = None
        updated_fields.append("event")
    elif event_name is not None and event_name.strip() and meta_editable:
        loan.event = get_or_create_event(session, event_name)
        updated_fields.append("event")
    if update_wish_pickup_on or update_wish_return_on:
        if loan.phase == LOAN_PHASE_DRAFT or manager_edit:
            if update_wish_pickup_on:
                loan.wish_pickup_on = wish_pickup_on
                updated_fields.append("wishPickupOn")
            if update_wish_return_on and effective_kind != LOAN_KIND_PERMANENT:
                loan.wish_return_on = wish_return_on
                updated_fields.append("wishReturnOn")
        elif update_wish_pickup_on or update_wish_return_on:
            raise ValueError("invalid_loan_state")
    if manager_edit:
        if update_pickup_on:
            loan.pickup_on = pickup_on
            updated_fields.append("pickupOn")
        if update_return_on and effective_kind != LOAN_KIND_PERMANENT:
            loan.return_on = return_on
            updated_fields.append("returnOn")
    if update_contact:
        if not manager_edit:
            raise ValueError("forbidden")
        if contact_user_id is None:
            loan.contact_user_id = None
        else:
            from lamathek.services.users import user_has_login

            contact = session.get(User, contact_user_id)
            if (
                contact is None
                or not user_has_login(contact)
                or not user_can_manage_inventory(session, contact, loan.inventory)
            ):
                raise ValueError("invalid_contact")
            loan.contact_user_id = contact_user_id
        updated_fields.append("contact")
    if update_pickup_note:
        loan.pickup_note = (pickup_note or "").strip()
        updated_fields.append("pickupNote")
    if update_return_note:
        loan.return_note = (return_note or "").strip()
        updated_fields.append("returnNote")
    if actor is not None and updated_fields:
        from lamathek.services.journal import append_journal

        append_journal(
            session,
            "loan.updated",
            actor,
            {"fields": updated_fields},
            loan_id=loan.id,
        )
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def piece_ids_marked_lost(session: Session, piece_ids: list[int]) -> set[int]:
    return piece_ids_with_open_total_loss(session, piece_ids)


def _stock_quantity(session: Session, material_type_id: int) -> int:
    from lamathek.services.material import total_stock_quantity

    return total_stock_quantity(session, material_type_id)


def _set_reserved_stock(session: Session, inventory_id: int, material_type_id: int) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(SetStockLine.quantity), 0))
        .join(MaterialSet)
        .where(
            MaterialSet.inventory_id == inventory_id,
            SetStockLine.material_type_id == material_type_id,
        )
    )
    return int(total or 0)


def _set_reserved_stock_for_role(
    session: Session, inventory_id: int, material_type_id: int, role: str
) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(SetStockLine.quantity), 0))
        .join(MaterialSet)
        .where(
            MaterialSet.inventory_id == inventory_id,
            SetStockLine.material_type_id == material_type_id,
            SetStockLine.role == role,
        )
    )
    return int(total or 0)


def _committed_set_origin_stock(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    origin_role: str,
    *,
    exclude_loan_id: int | None = None,
) -> int:
    stmt = (
        select(LoanLine)
        .join(Loan)
        .where(
            Loan.inventory_id == inventory_id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_not(None),
            LoanLine.origin_set_role == origin_role,
            LoanLine.status.in_(LINE_STATUSES_BLOCKING),
        )
    )
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    total = 0
    for line in session.scalars(stmt).all():
        if line.quantity is not None:
            total += line.quantity
    return total


def _committed_set_origin_stock_total(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    *,
    exclude_loan_id: int | None = None,
) -> int:
    stmt = (
        select(LoanLine)
        .join(Loan)
        .where(
            Loan.inventory_id == inventory_id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_not(None),
            LoanLine.status.in_(LINE_STATUSES_BLOCKING),
        )
    )
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    total = 0
    for line in session.scalars(stmt).all():
        total += line.quantity or 0
    return total


def _loaned_stock_loose(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    *,
    exclude_loan_id: int | None = None,
) -> int:
    stmt = (
        select(LoanLine)
        .join(Loan)
        .where(
            Loan.inventory_id == inventory_id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_(None),
            LoanLine.status.in_(LINE_STATUSES_BLOCKING),
        )
    )
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    total = 0
    for line in session.scalars(stmt).all():
        total += line.quantity or 0
    return total


def minimum_stock_quantity(
    session: Session, inventory_id: int, material_type_id: int
) -> int:
    reserved = _set_reserved_stock(session, inventory_id, material_type_id)
    committed_sets = _committed_set_origin_stock_total(
        session, inventory_id, material_type_id
    )
    loaned_loose = _loaned_stock_loose(session, inventory_id, material_type_id)
    return max(reserved, committed_sets) + loaned_loose


def piece_on_open_loan(session: Session, piece_id: int) -> bool:
    stmt = select(LoanLine).join(Loan).where(LoanLine.piece_id == piece_id)
    for line in session.scalars(stmt).all():
        if line.status in LINE_STATUSES_BLOCKING:
            return True
        if line.status == LINE_STATUS_DRAFT:
            return True
    return False


def _validate_stock_available(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    additional_quantity: int,
    *,
    exclude_loan_id: int | None = None,
    from_set_origin: bool = False,
) -> None:
    available = _stock_quantity(session, material_type_id)
    committed_sets = _committed_set_origin_stock_total(
        session, inventory_id, material_type_id, exclude_loan_id=exclude_loan_id
    )
    loaned_loose = _loaned_stock_loose(
        session, inventory_id, material_type_id, exclude_loan_id=exclude_loan_id
    )
    if from_set_origin:
        needed = committed_sets + loaned_loose + additional_quantity
    else:
        reserved_sets = _set_reserved_stock(session, inventory_id, material_type_id)
        needed = max(reserved_sets, committed_sets) + loaned_loose + additional_quantity
    if needed > available:
        raise ValueError("over_loaned")


def _validate_piece_available(
    session: Session, piece_id: int, *, exclude_loan_id: int | None = None
) -> None:
    piece = session.get(Piece, piece_id)
    if piece is not None and piece.status == ITEM_STATUS_RETIRED:
        raise ValueError("piece_unavailable")
    if piece_is_blocked_for_lending(session, piece_id):
        raise ValueError("piece_unavailable")
    if piece_blocked_on_loan(session, piece_id, exclude_loan_id=exclude_loan_id):
        raise ValueError("piece_unavailable")


def _origin_fields(material_set: MaterialSet, role: str) -> dict:
    return {
        "origin_set_id": material_set.id,
        "origin_set_name": material_set.name,
        "origin_set_role": role,
    }


def _loan_editable_for_lines(loan: Loan) -> bool:
    return loan.phase in (LOAN_PHASE_DRAFT, LOAN_PHASE_REVIEW, LOAN_PHASE_PACK)


def _piece_line_on_loan(session: Session, loan_id: int, piece_id: int) -> LoanLine | None:
    return session.scalar(
        select(LoanLine).where(
            LoanLine.loan_id == loan_id,
            LoanLine.piece_id == piece_id,
        )
    )


def _reopen_withdrawn_piece(
    line: LoanLine, *, status: str, origin: dict | None = None
) -> LoanLine:
    line.status = status
    line.reason = ""
    line.request_notified = False
    line.mail_pending = False
    if origin is not None:
        line.origin_set_id = origin["origin_set_id"]
        line.origin_set_name = origin["origin_set_name"]
        line.origin_set_role = origin["origin_set_role"]
    return line


def _place_piece_on_loan(
    session: Session,
    loan: Loan,
    piece_id: int,
    *,
    status: str,
    origin: dict | None = None,
) -> LoanLine:
    existing = _piece_line_on_loan(session, loan.id, piece_id)
    if existing is None:
        line = LoanLine(loan_id=loan.id, piece_id=piece_id, status=status, **(origin or {}))
        session.add(line)
        return line
    if existing.status != LINE_STATUS_WITHDRAWN:
        raise ValueError("line_exists")
    return _reopen_withdrawn_piece(existing, status=status, origin=origin)


def _place_set_piece(
    session: Session,
    loan: Loan,
    piece_id: int,
    *,
    status: str,
    origin: dict,
) -> None:
    existing = _piece_line_on_loan(session, loan.id, piece_id)
    if existing is not None and existing.status != LINE_STATUS_WITHDRAWN:
        return
    _place_piece_on_loan(session, loan, piece_id, status=status, origin=origin)


def _place_set_stock(
    session: Session,
    loan: Loan,
    *,
    material_type_id: int,
    quantity: int,
    status: str,
    origin: dict,
) -> None:
    lines = session.scalars(
        select(LoanLine).where(
            LoanLine.loan_id == loan.id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id == origin["origin_set_id"],
            LoanLine.origin_set_role == origin["origin_set_role"],
        )
    ).all()
    if any(line.status != LINE_STATUS_WITHDRAWN for line in lines):
        return
    withdrawn = next((line for line in lines if line.status == LINE_STATUS_WITHDRAWN), None)
    if withdrawn is not None:
        withdrawn.status = status
        withdrawn.quantity = quantity
        withdrawn.reason = ""
        withdrawn.request_notified = False
        withdrawn.mail_pending = False
        return
    session.add(
        LoanLine(
            loan_id=loan.id,
            material_type_id=material_type_id,
            quantity=quantity,
            status=status,
            **origin,
        )
    )


def add_set_assignment_lines(session: Session, loan: Loan, set_id: int) -> None:
    if not _loan_editable_for_lines(loan):
        raise ValueError("loan_not_editable")
    material_set = load_set_by_id(session, set_id)
    if material_set is None or material_set.inventory_id != loan.inventory_id:
        raise ValueError("invalid_set")

    status = new_line_status_for_loan(loan)
    origin = _origin_fields(material_set, ORIGIN_SET_ROLE_ASSIGNMENT)
    for piece in material_set.pieces:
        if piece.set_role != SET_ROLE_ASSIGNMENT:
            continue
        _place_set_piece(session, loan, piece.id, status=status, origin=origin)
    for stock_line in material_set.stock_lines:
        if stock_line.role != SET_ROLE_ASSIGNMENT:
            continue
        _place_set_stock(
            session,
            loan,
            material_type_id=stock_line.material_type_id,
            quantity=stock_line.quantity,
            status=status,
            origin=origin,
        )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("line_exists") from None


def add_set_optional_lines(session: Session, loan: Loan, set_id: int) -> None:
    if not _loan_editable_for_lines(loan):
        raise ValueError("loan_not_editable")
    material_set = load_set_by_id(session, set_id)
    if material_set is None or material_set.inventory_id != loan.inventory_id:
        raise ValueError("invalid_set")

    status = new_line_status_for_loan(loan)
    origin = _origin_fields(material_set, ORIGIN_SET_ROLE_OPTIONAL)
    for piece in material_set.pieces:
        if piece.set_role != SET_ROLE_OPTIONAL:
            continue
        _place_set_piece(session, loan, piece.id, status=status, origin=origin)
    for stock_line in material_set.stock_lines:
        if stock_line.role != SET_ROLE_OPTIONAL:
            continue
        _place_set_stock(
            session,
            loan,
            material_type_id=stock_line.material_type_id,
            quantity=stock_line.quantity,
            status=status,
            origin=origin,
        )
    session.commit()


def add_piece_line(session: Session, loan: Loan, piece_id: int) -> LoanLine:
    if not _loan_editable_for_lines(loan):
        raise ValueError("loan_not_editable")
    piece = session.get(Piece, piece_id)
    if piece is None or piece.material_type.inventory_id != loan.inventory_id:
        raise ValueError("invalid_piece")
    status = new_line_status_for_loan(loan)
    piece = session.get(Piece, piece_id)
    if piece is not None and piece.status == ITEM_STATUS_RETIRED:
        raise ValueError("piece_unavailable")
    if piece_is_blocked_for_lending(session, piece_id):
        raise ValueError("piece_unavailable")
    if status != LINE_STATUS_DRAFT and piece_blocked_on_loan(
        session, piece_id, exclude_loan_id=loan.id
    ):
        raise ValueError("piece_unavailable")
    try:
        line = _place_piece_on_loan(session, loan, piece_id, status=status)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("line_exists") from None
    except ValueError:
        session.rollback()
        raise
    session.refresh(line)
    return line


def add_stock_line(session: Session, loan: Loan, material_type_id: int, quantity: int) -> LoanLine:
    if not _loan_editable_for_lines(loan):
        raise ValueError("loan_not_editable")
    if quantity <= 0:
        raise ValueError("invalid_quantity")
    from lamathek.models.material import MaterialType, TRACKING_STOCK

    mt = session.get(MaterialType, material_type_id)
    if mt is None or mt.inventory_id != loan.inventory_id or mt.tracking != TRACKING_STOCK:
        raise ValueError("invalid_material_type")
    status = new_line_status_for_loan(loan)
    existing = session.scalar(
        select(LoanLine).where(
            LoanLine.loan_id == loan.id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_(None),
            LoanLine.status.in_((LINE_STATUS_DRAFT, LINE_STATUS_REQUESTED)),
        )
    )
    if existing is not None:
        if existing.quantity != quantity and existing.request_notified:
            existing.request_notified = False
        existing.quantity = quantity
        session.commit()
        return existing
    withdrawn = session.scalar(
        select(LoanLine).where(
            LoanLine.loan_id == loan.id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_(None),
            LoanLine.status == LINE_STATUS_WITHDRAWN,
        )
    )
    if withdrawn is not None:
        withdrawn.status = status
        withdrawn.quantity = quantity
        withdrawn.reason = ""
        withdrawn.request_notified = False
        withdrawn.mail_pending = False
        session.commit()
        return withdrawn
    line = LoanLine(
        loan_id=loan.id,
        material_type_id=material_type_id,
        quantity=quantity,
        status=status,
    )
    session.add(line)
    session.commit()
    session.refresh(line)
    return line


def restore_withdrawn_line(
    session: Session, loan: Loan, line_id: int, *, actor: User | None = None
) -> Loan:
    line = session.get(LoanLine, line_id)
    if line is None or line.loan_id != loan.id:
        raise ValueError("invalid_line")
    if line.status != LINE_STATUS_WITHDRAWN:
        raise ValueError("invalid_line_status")
    assert_line_action_allowed(loan, line, "restore")
    if line.piece_id is not None:
        add_piece_line(session, loan, line.piece_id)
        return loan_by_id(session, loan.id)  # type: ignore[return-value]
    if line.material_type_id is None or line.quantity is None:
        raise ValueError("invalid_line")
    if not _loan_editable_for_lines(loan):
        raise ValueError("loan_not_editable")
    line.status = new_line_status_for_loan(loan)
    line.reason = ""
    line.request_notified = False
    line.mail_pending = False
    if actor is not None:
        from lamathek.services.journal import journal_line_action

        journal_line_action(
            session,
            actor=actor,
            loan_id=loan.id,
            line=line,
            action="restore_withdrawn",
        )
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def remove_line(session: Session, loan: Loan, line_id: int) -> None:
    if loan.phase == LOAN_PHASE_CLOSED:
        raise ValueError("loan_not_editable")
    line = session.get(LoanLine, line_id)
    if line is None or line.loan_id != loan.id:
        raise ValueError("not_found")
    if line.status != LINE_STATUS_DRAFT:
        raise ValueError("loan_not_editable")
    session.delete(line)
    session.commit()
