from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.damage import Damage, Repair
from lamathek.models.material import MaterialType, Piece
def piece_has_open_severe_damage(session: Session, piece_id: int) -> bool:
    damages = session.scalars(
        select(Damage)
        .where(Damage.piece_id == piece_id, Damage.severe.is_(True))
        .options(selectinload(Damage.repair))
    ).all()
    return any(damage.repair is None for damage in damages)


def create_damage(
    session: Session,
    piece: Piece,
    recorded_on: date,
    *,
    note: str | None,
    severe: bool,
) -> Damage:
    damage = Damage(
        piece_id=piece.id,
        recorded_on=recorded_on,
        note=note,
        severe=severe,
    )
    session.add(damage)
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
) -> Repair:
    if damage.repair is not None:
        raise ValueError("already_repaired")
    repair = Repair(
        damage_id=damage.id,
        recorded_on=recorded_on,
        note=note,
    )
    session.add(repair)
    session.commit()
    return repair
