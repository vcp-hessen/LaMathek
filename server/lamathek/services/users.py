from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lamathek.models.user import User


def upsert_user_from_oidc(
    session: Session,
    *,
    sub: str,
    name: str | None,
    email: str | None,
    force_superuser: bool | None = None,
) -> User:
    user = session.scalar(select(User).where(User.oidc_sub == sub))
    if user is None:
        user = User(oidc_sub=sub)
        session.add(user)
    user.name = name
    user.email = email

    if force_superuser is not None:
        user.is_superuser = force_superuser
    else:
        superuser_count = session.scalar(
            select(func.count()).select_from(User).where(User.is_superuser.is_(True))
        )
        if superuser_count == 0:
            user.is_superuser = True

    session.commit()
    session.refresh(user)
    return user


def user_by_oidc_sub(session: Session, sub: str) -> User | None:
    return session.scalar(select(User).where(User.oidc_sub == sub))


def user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def count_superusers(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(User).where(User.is_superuser.is_(True))
    ) or 0


def set_superuser(session: Session, user: User, is_superuser: bool) -> None:
    if user.is_superuser and not is_superuser and count_superusers(session) <= 1:
        raise ValueError("cannot_remove_last_superuser")
    user.is_superuser = is_superuser
    session.commit()


def search_users(session: Session, query: str, *, limit: int = 20) -> list[User]:
    trimmed = query.strip()
    if len(trimmed) < 2:
        return []
    pattern = f"%{trimmed}%"
    return list(
        session.scalars(
            select(User)
            .where(
                (User.name.ilike(pattern)) | (User.email.ilike(pattern)),
            )
            .order_by(User.name, User.email)
            .limit(limit)
        ).all()
    )
