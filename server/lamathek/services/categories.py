from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lamathek.models.category import Category


def list_categories(session: Session) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name)).all())


def get_or_create_category(session: Session, name: str) -> Category:
    trimmed = name.strip()
    existing = session.scalar(select(Category).where(Category.name == trimmed))
    if existing is not None:
        return existing
    category = Category(name=trimmed)
    session.add(category)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(Category).where(Category.name == trimmed))
        if existing is None:
            raise
        return existing
    return category


def resolve_category_id(
    session: Session,
    *,
    category_id: int | None = None,
    category_name: str | None = None,
    clear: bool = False,
) -> int | None:
    if clear:
        return None
    if category_id is not None:
        if session.get(Category, category_id) is None:
            raise ValueError("invalid_category")
        return category_id
    if category_name is not None and category_name.strip():
        return get_or_create_category(session, category_name).id
    return None
