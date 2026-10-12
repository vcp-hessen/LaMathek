from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from lamathek.models.inventory import Inventory
from lamathek.models.loan import (
    LOAN_KIND_PERMANENT,
    LOAN_KIND_SHORT,
    LOAN_STATUS_CLOSED,
    LOAN_STATUS_HANDED_OUT,
    LOAN_STATUS_PLANNED,
    ORIGIN_SET_ROLE_ASSIGNMENT,
    ORIGIN_SET_ROLE_OPTIONAL,
    VALID_LOAN_KINDS,
    RETURN_OUTCOME_LOSS,
    RETURN_OUTCOME_RETURNED,
    VALID_RETURN_OUTCOMES,
    Event,
    Group,
    Loan,
    LoanLine,
    LoanReturn,
    LoanReturnLine,
)
from lamathek.models.material import ITEM_STATUS_RETIRED, Piece
from lamathek.models.set import (
    SET_ROLE_ASSIGNMENT,
    SET_ROLE_OPTIONAL,
    MaterialSet,
    SetStockLine,
)
from lamathek.models.user import User
from lamathek.services.damages import piece_has_open_severe_damage
from lamathek.services.sets import set_by_id as load_set_by_id


def _loan_query():
    return select(Loan).options(
        selectinload(Loan.group),
        selectinload(Loan.event),
        selectinload(Loan.responsible_user),
        selectinload(Loan.lines).selectinload(LoanLine.piece).selectinload(Piece.material_type),
        selectinload(Loan.lines).selectinload(LoanLine.material_type),
        selectinload(Loan.lines).selectinload(LoanLine.return_lines),
        selectinload(Loan.returns).selectinload(LoanReturn.lines),
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


def _validate_responsible(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("invalid_responsible")
    return user


def create_loan(
    session: Session,
    inventory: Inventory,
    *,
    group_name: str,
    responsible_user_id: int,
    event_name: str | None,
    starts_on: date | None,
    ends_on: date | None,
    kind: str = LOAN_KIND_SHORT,
) -> Loan:
    if kind not in VALID_LOAN_KINDS:
        raise ValueError("invalid_kind")
    if kind == LOAN_KIND_PERMANENT:
        if (
            (event_name is not None and event_name.strip())
            or starts_on is not None
            or ends_on is not None
        ):
            raise ValueError("invalid_permanent_fields")
        event_name = None
        starts_on = None
        ends_on = None
    elif starts_on is not None and ends_on is not None and ends_on < starts_on:
        raise ValueError("invalid_date_range")
    _validate_responsible(session, responsible_user_id)
    group = get_or_create_group(session, group_name)
    event = None
    if event_name is not None and event_name.strip():
        event = get_or_create_event(session, event_name)
    loan = Loan(
        inventory_id=inventory.id,
        group_id=group.id,
        responsible_user_id=responsible_user_id,
        event_id=event.id if event else None,
        status=LOAN_STATUS_PLANNED,
        kind=kind,
        starts_on=starts_on,
        ends_on=ends_on,
    )
    session.add(loan)
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def update_loan(
    session: Session,
    loan: Loan,
    *,
    group_name: str | None = None,
    responsible_user_id: int | None = None,
    event_name: str | None = None,
    clear_event: bool = False,
    starts_on: date | None = None,
    ends_on: date | None = None,
    update_starts_on: bool = False,
    update_ends_on: bool = False,
    kind: str | None = None,
) -> Loan:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    if kind is not None:
        if kind not in VALID_LOAN_KINDS:
            raise ValueError("invalid_kind")
        loan.kind = kind
    effective_kind = kind if kind is not None else loan.kind
    if effective_kind == LOAN_KIND_PERMANENT:
        if clear_event or (event_name is not None and event_name.strip()):
            raise ValueError("invalid_permanent_fields")
        if update_starts_on and starts_on is not None:
            raise ValueError("invalid_permanent_fields")
        if update_ends_on and ends_on is not None:
            raise ValueError("invalid_permanent_fields")
    if update_starts_on or update_ends_on:
        new_start = starts_on if update_starts_on else loan.starts_on
        new_end = ends_on if update_ends_on else loan.ends_on
        if new_start is not None and new_end is not None and new_end < new_start:
            raise ValueError("invalid_date_range")
    if group_name is not None:
        loan.group = get_or_create_group(session, group_name)
    if responsible_user_id is not None:
        _validate_responsible(session, responsible_user_id)
        loan.responsible_user_id = responsible_user_id
    if clear_event:
        loan.event_id = None
    elif event_name is not None and event_name.strip():
        loan.event = get_or_create_event(session, event_name)
    if update_starts_on:
        loan.starts_on = starts_on
    if update_ends_on:
        loan.ends_on = ends_on
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def _line_return_totals(session: Session, loan_line_id: int) -> tuple[int, int]:
    returned = 0
    lost = 0
    rows = session.scalars(
        select(LoanReturnLine).where(LoanReturnLine.loan_line_id == loan_line_id)
    ).all()
    for row in rows:
        qty = row.quantity if row.quantity is not None else 1
        if row.outcome == RETURN_OUTCOME_RETURNED:
            returned += qty
        elif row.outcome == RETURN_OUTCOME_LOSS:
            lost += qty
    return returned, lost


def _line_is_settled(session: Session, line: LoanLine) -> bool:
    if line.material_type_id is not None and line.quantity is not None:
        returned, lost = _line_return_totals(session, line.id)
        return returned + lost >= line.quantity
    returned, lost = _line_return_totals(session, line.id)
    return returned + lost >= 1


def _line_stock_outstanding(session: Session, line: LoanLine) -> int:
    if line.quantity is None:
        return 0
    returned, lost = _line_return_totals(session, line.id)
    return max(0, line.quantity - returned - lost)


def _piece_lost(session: Session, piece_id: int) -> bool:
    direct = session.scalar(
        select(LoanReturnLine.id)
        .join(LoanLine)
        .where(
            LoanLine.piece_id == piece_id,
            LoanReturnLine.outcome == RETURN_OUTCOME_LOSS,
        )
    )
    return direct is not None


def _piece_handed_out(session: Session, piece_id: int, *, exclude_loan_id: int | None = None) -> bool:
    if _piece_lost(session, piece_id):
        return False
    stmt = (
        select(LoanLine.id)
        .join(Loan)
        .where(
            LoanLine.piece_id == piece_id,
            Loan.status == LOAN_STATUS_HANDED_OUT,
        )
    )
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    for line_id in session.scalars(stmt).all():
        line = session.get(LoanLine, line_id)
        if line is not None and not _line_is_settled(session, line):
            return True
    return False


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
            Loan.status.in_((LOAN_STATUS_PLANNED, LOAN_STATUS_HANDED_OUT)),
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_not(None),
            LoanLine.origin_set_role == origin_role,
        )
        .options(selectinload(LoanLine.loan))
    )
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    total = 0
    for line in session.scalars(stmt).all():
        if line.quantity is None:
            continue
        if line.loan.status == LOAN_STATUS_PLANNED:
            total += line.quantity
        elif line.loan.status == LOAN_STATUS_HANDED_OUT:
            total += _line_stock_outstanding(session, line)
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
            Loan.status == LOAN_STATUS_HANDED_OUT,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_(None),
        )
    )
    if exclude_loan_id is not None:
        stmt = stmt.where(Loan.id != exclude_loan_id)
    total = 0
    for line in session.scalars(stmt).all():
        total += _line_stock_outstanding(session, line)
    return total


def _planned_loose_stock(
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
            Loan.status == LOAN_STATUS_PLANNED,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_(None),
            LoanLine.quantity.is_not(None),
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
    loaned_loose = _loaned_stock_loose(session, inventory_id, material_type_id)
    planned_loose = _planned_loose_stock(session, inventory_id, material_type_id)
    return reserved + loaned_loose + planned_loose


def piece_on_open_loan(session: Session, piece_id: int) -> bool:
    stmt = (
        select(LoanLine)
        .join(Loan)
        .where(
            LoanLine.piece_id == piece_id,
            Loan.status.in_((LOAN_STATUS_PLANNED, LOAN_STATUS_HANDED_OUT)),
        )
        .options(selectinload(LoanLine.loan))
    )
    for line in session.scalars(stmt).all():
        if line.loan.status == LOAN_STATUS_PLANNED:
            return True
        if line.loan.status == LOAN_STATUS_HANDED_OUT and not _line_is_settled(
            session, line
        ):
            return True
    return False


def _validate_stock_available(
    session: Session,
    inventory_id: int,
    material_type_id: int,
    additional_quantity: int,
    *,
    exclude_loan_id: int | None = None,
) -> None:
    available = _stock_quantity(session, material_type_id)
    reserved_sets = _set_reserved_stock(session, inventory_id, material_type_id)
    loaned_loose = _loaned_stock_loose(
        session, inventory_id, material_type_id, exclude_loan_id=exclude_loan_id
    )
    planned_loose = _planned_loose_stock(
        session, inventory_id, material_type_id, exclude_loan_id=exclude_loan_id
    )
    if reserved_sets + loaned_loose + planned_loose + additional_quantity > available:
        raise ValueError("over_loaned")


def _validate_piece_available(
    session: Session, piece_id: int, *, exclude_loan_id: int | None = None
) -> None:
    piece = session.get(Piece, piece_id)
    if piece is not None and piece.status == ITEM_STATUS_RETIRED:
        raise ValueError("piece_unavailable")
    if piece_has_open_severe_damage(session, piece_id):
        raise ValueError("piece_unavailable")
    if _piece_lost(session, piece_id):
        raise ValueError("piece_unavailable")
    if _piece_handed_out(session, piece_id, exclude_loan_id=exclude_loan_id):
        raise ValueError("piece_unavailable")


def _origin_fields(material_set: MaterialSet, role: str) -> dict:
    return {
        "origin_set_id": material_set.id,
        "origin_set_name": material_set.name,
        "origin_set_role": role,
    }


def _loan_has_set_assignment(session: Session, loan_id: int, set_id: int) -> bool:
    return (
        session.scalar(
            select(LoanLine.id).where(
                LoanLine.loan_id == loan_id,
                LoanLine.origin_set_id == set_id,
                LoanLine.origin_set_role == ORIGIN_SET_ROLE_ASSIGNMENT,
            )
        )
        is not None
    )


def _loan_has_piece(session: Session, loan_id: int, piece_id: int) -> bool:
    return (
        session.scalar(
            select(LoanLine.id).where(
                LoanLine.loan_id == loan_id,
                LoanLine.piece_id == piece_id,
            )
        )
        is not None
    )


def add_set_assignment_lines(session: Session, loan: Loan, set_id: int) -> None:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    material_set = load_set_by_id(session, set_id)
    if material_set is None or material_set.inventory_id != loan.inventory_id:
        raise ValueError("invalid_set")
    if _loan_has_set_assignment(session, loan.id, set_id):
        raise ValueError("set_already_added")

    origin = _origin_fields(material_set, ORIGIN_SET_ROLE_ASSIGNMENT)
    for piece in material_set.pieces:
        if piece.set_role != SET_ROLE_ASSIGNMENT:
            continue
        _validate_piece_available(session, piece.id, exclude_loan_id=loan.id)
        session.add(LoanLine(loan_id=loan.id, piece_id=piece.id, **origin))
    for stock_line in material_set.stock_lines:
        if stock_line.role != SET_ROLE_ASSIGNMENT:
            continue
        session.add(
            LoanLine(
                loan_id=loan.id,
                material_type_id=stock_line.material_type_id,
                quantity=stock_line.quantity,
                **origin,
            )
        )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("line_exists") from None


def add_set_optional_lines(session: Session, loan: Loan, set_id: int) -> None:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    material_set = load_set_by_id(session, set_id)
    if material_set is None or material_set.inventory_id != loan.inventory_id:
        raise ValueError("invalid_set")

    origin = _origin_fields(material_set, ORIGIN_SET_ROLE_OPTIONAL)
    for piece in material_set.pieces:
        if piece.set_role != SET_ROLE_OPTIONAL:
            continue
        if _loan_has_piece(session, loan.id, piece.id):
            continue
        _validate_piece_available(session, piece.id, exclude_loan_id=loan.id)
        session.add(LoanLine(loan_id=loan.id, piece_id=piece.id, **origin))
    for stock_line in material_set.stock_lines:
        if stock_line.role != SET_ROLE_OPTIONAL:
            continue
        session.add(
            LoanLine(
                loan_id=loan.id,
                material_type_id=stock_line.material_type_id,
                quantity=stock_line.quantity,
                **origin,
            )
        )
    session.commit()


def add_piece_line(session: Session, loan: Loan, piece_id: int) -> LoanLine:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    piece = session.get(Piece, piece_id)
    if piece is None or piece.material_type.inventory_id != loan.inventory_id:
        raise ValueError("invalid_piece")
    _validate_piece_available(session, piece_id)
    line = LoanLine(loan_id=loan.id, piece_id=piece_id)
    session.add(line)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("line_exists") from None
    session.refresh(line)
    return line


def add_stock_line(session: Session, loan: Loan, material_type_id: int, quantity: int) -> LoanLine:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    if quantity <= 0:
        raise ValueError("invalid_quantity")
    from lamathek.models.material import MaterialType, TRACKING_STOCK

    mt = session.get(MaterialType, material_type_id)
    if mt is None or mt.inventory_id != loan.inventory_id or mt.tracking != TRACKING_STOCK:
        raise ValueError("invalid_material_type")
    existing = session.scalar(
        select(LoanLine).where(
            LoanLine.loan_id == loan.id,
            LoanLine.material_type_id == material_type_id,
            LoanLine.origin_set_id.is_(None),
        )
    )
    if existing is not None:
        existing.quantity = quantity
        session.commit()
        return existing
    line = LoanLine(
        loan_id=loan.id,
        material_type_id=material_type_id,
        quantity=quantity,
    )
    session.add(line)
    session.commit()
    session.refresh(line)
    return line


def remove_line(session: Session, loan: Loan, line_id: int) -> None:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    line = session.get(LoanLine, line_id)
    if line is None or line.loan_id != loan.id:
        raise ValueError("not_found")
    session.delete(line)
    session.commit()


def hand_out_loan(session: Session, loan: Loan) -> Loan:
    if loan.status != LOAN_STATUS_PLANNED:
        raise ValueError("loan_not_editable")
    loan = loan_by_id(session, loan.id)
    if loan is None:
        raise ValueError("not_found")
    if not loan.lines:
        raise ValueError("empty_loan")

    stock_totals: dict[int, int] = {}
    origin_stock_totals: dict[tuple[int, str], int] = {}
    for line in loan.lines:
        if line.piece_id is not None:
            _validate_piece_available(session, line.piece_id, exclude_loan_id=loan.id)
        elif line.material_type_id is not None and line.quantity is not None:
            if line.origin_set_id is None:
                stock_totals[line.material_type_id] = (
                    stock_totals.get(line.material_type_id, 0) + line.quantity
                )
            elif line.origin_set_role is not None:
                key = (line.material_type_id, line.origin_set_role)
                origin_stock_totals[key] = origin_stock_totals.get(key, 0) + line.quantity

    for (material_type_id, origin_role), qty in origin_stock_totals.items():
        reserved = _set_reserved_stock_for_role(
            session, loan.inventory_id, material_type_id, origin_role
        )
        committed = _committed_set_origin_stock(
            session,
            loan.inventory_id,
            material_type_id,
            origin_role,
            exclude_loan_id=loan.id,
        )
        if committed + qty > reserved:
            raise ValueError("over_loaned")

    for material_type_id, qty in stock_totals.items():
        _validate_stock_available(
            session,
            loan.inventory_id,
            material_type_id,
            qty,
            exclude_loan_id=loan.id,
        )

    loan.status = LOAN_STATUS_HANDED_OUT
    session.commit()
    return loan_by_id(session, loan.id)  # type: ignore[return-value]


def _maybe_close_loan(session: Session, loan: Loan) -> None:
    loan = loan_by_id(session, loan.id)
    if loan is None or loan.status != LOAN_STATUS_HANDED_OUT:
        return
    for line in loan.lines:
        if not _line_is_settled(session, line):
            return
    loan.status = LOAN_STATUS_CLOSED
    session.commit()


def record_loan_return(
    session: Session,
    loan: Loan,
    recorded_on: date,
    entries: list[dict],
) -> Loan:
    if loan.status != LOAN_STATUS_HANDED_OUT:
        raise ValueError("loan_not_returnable")

    loan = loan_by_id(session, loan.id)
    if loan is None:
        raise ValueError("not_found")

    if not entries:
        raise ValueError("empty_return")

    loan_return = LoanReturn(loan_id=loan.id, recorded_on=recorded_on)
    session.add(loan_return)
    session.flush()

    line_ids = {line.id for line in loan.lines}

    for entry in entries:
        loan_line_id = entry.get("loanLineId")
        outcome = entry.get("outcome")
        quantity = entry.get("quantity")

        if loan_line_id not in line_ids:
            raise ValueError("invalid_line")
        if outcome not in VALID_RETURN_OUTCOMES:
            raise ValueError("invalid_outcome")

        line = session.get(LoanLine, loan_line_id)
        if line is None:
            raise ValueError("invalid_line")

        if line.material_type_id is not None:
            if not isinstance(quantity, int) or quantity <= 0:
                raise ValueError("invalid_quantity")
            outstanding = _line_stock_outstanding(session, line)
            if quantity > outstanding:
                raise ValueError("over_returned")
            return_qty = quantity if outcome == RETURN_OUTCOME_RETURNED else None
            loss_qty = quantity if outcome == RETURN_OUTCOME_LOSS else None
            if outcome == RETURN_OUTCOME_RETURNED:
                session.add(
                    LoanReturnLine(
                        loan_return_id=loan_return.id,
                        loan_line_id=line.id,
                        outcome=outcome,
                        quantity=return_qty,
                    )
                )
            else:
                session.add(
                    LoanReturnLine(
                        loan_return_id=loan_return.id,
                        loan_line_id=line.id,
                        outcome=outcome,
                        quantity=loss_qty,
                    )
                )
                from lamathek.services.material import apply_stock_loss

                apply_stock_loss(session, line.material_type_id, quantity)
        else:
            if _line_is_settled(session, line):
                raise ValueError("line_already_settled")
            if quantity is not None:
                raise ValueError("invalid_quantity")
            session.add(
                LoanReturnLine(
                    loan_return_id=loan_return.id,
                    loan_line_id=line.id,
                    outcome=outcome,
                    quantity=None,
                )
            )

    session.commit()
    _maybe_close_loan(session, loan)
    return loan_by_id(session, loan.id)  # type: ignore[return-value]
