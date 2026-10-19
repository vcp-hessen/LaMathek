from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.damage import (
    DAMAGE_KIND_DAMAGE,
    RESOLUTION_REPAIRED,
    Damage,
    Repair,
)
from lamathek.models.material import MaterialType, Piece
from lamathek.models.user import User
from lamathek.services.journal import append_journal


def create_damage(
    session: Session,
    piece: Piece,
    recorded_on: date,
    *,
    note: str | None,
    severe: bool,
    actor: User | None = None,
) -> Damage:
    damage = Damage(
        piece_id=piece.id,
        recorded_on=recorded_on,
        note=note,
        severe=severe,
        kind=DAMAGE_KIND_DAMAGE,
    )
    session.add(damage)
    session.flush()
    append_journal(
        session,
        "damage.created",
        actor,
        {"damageId": damage.id, "severe": severe, "note": note or ""},
        piece_id=piece.id,
        loan_id=damage.loan_id,
        loan_line_id=damage.loan_line_id,
    )
    session.commit()
    return session.scalar(
        select(Damage)
        .where(Damage.id == damage.id)
        .options(selectinload(Damage.repair), selectinload(Damage.photos))
    )  # type: ignore[return-value]


def damage_by_id(session: Session, damage_id: int) -> Damage | None:
    return session.scalar(
        select(Damage)
        .where(Damage.id == damage_id)
        .options(
            selectinload(Damage.repair),
            selectinload(Damage.photos),
            selectinload(Damage.piece)
            .selectinload(Piece.material_type)
            .selectinload(MaterialType.inventory),
        )
    )


def create_repair(
    session: Session,
    damage: Damage,
    recorded_on: date,
    *,
    note: str | None,
    actor: User | None = None,
) -> Repair:
    if damage.repair is not None:
        raise ValueError("already_repaired")
    repair = Repair(
        damage_id=damage.id,
        recorded_on=recorded_on,
        note=note,
        resolution_kind=RESOLUTION_REPAIRED,
    )
    session.add(repair)
    session.flush()
    append_journal(
        session,
        "repair.created",
        actor,
        {
            "repairId": repair.id,
            "damageId": damage.id,
            "resolutionKind": repair.resolution_kind,
            "note": note or "",
        },
        piece_id=damage.piece_id,
        loan_id=damage.loan_id,
        loan_line_id=damage.loan_line_id,
    )
    session.commit()
    return repair
