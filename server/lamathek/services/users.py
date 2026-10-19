import uuid

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


def user_has_login(user: User) -> bool:
    return not (user.oidc_sub or "").startswith("local:")


def create_local_user(
    session: Session,
    *,
    name: str,
    phone: str,
    email: str | None = None,
) -> User:
    trimmed_name = name.strip()
    trimmed_phone = phone.strip()
    trimmed_email = email.strip() if isinstance(email, str) else ""
    if not trimmed_name or not trimmed_phone or not trimmed_email:
        raise ValueError("invalid_user")
    _require_unique_email(session, trimmed_email)
    user = User(
        oidc_sub=f"local:{uuid.uuid4()}",
        name=trimmed_name,
        phone=trimmed_phone,
        email=trimmed_email,
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def merge_local_user_into_login(
    session: Session, *, source_id: int, target_id: int
) -> User:
    from lamathek.models.loan import Loan

    if source_id == target_id:
        raise ValueError("invalid_merge")
    source = session.get(User, source_id)
    target = session.get(User, target_id)
    if source is None or target is None:
        raise ValueError("not_found")
    if user_has_login(source) or not user_has_login(target):
        raise ValueError("invalid_merge")
    from sqlalchemy import update

    from lamathek.models.audit import AuditEvent
    from lamathek.models.journal import LoanJournalEntry

    # Re-point every reference so nothing is lost to CASCADE or SET NULL.
    for model, column in (
        (Loan, Loan.borrower_user_id),
        (Loan, Loan.contact_user_id),
        (LoanJournalEntry, LoanJournalEntry.actor_user_id),
        (LoanJournalEntry, LoanJournalEntry.real_actor_user_id),
        (AuditEvent, AuditEvent.actor_user_id),
        (AuditEvent, AuditEvent.target_user_id),
    ):
        session.execute(
            update(model).where(column == source.id).values({column.key: target.id})
        )
    session.flush()
    session.expire_all()
    session.delete(source)
    session.commit()
    return target


def _require_unique_email(session: Session, email: str, *, except_user_id: int | None = None) -> None:
    taken = session.scalar(
        select(User.id).where(
            func.lower(User.email) == email.lower(),
            User.id != except_user_id,
        )
    )
    if taken is not None:
        raise ValueError("email_taken")


def update_user_phone(session: Session, user: User, phone: str) -> User:
    user.phone = phone.strip()
    session.commit()
    session.refresh(user)
    return user


def update_user_contact(
    session: Session,
    user: User,
    *,
    phone: str | None = None,
    email: str | None = None,
) -> User:
    if phone is not None:
        user.phone = phone.strip()
    if email is not None:
        trimmed = email.strip()
        if not trimmed:
            raise ValueError("invalid_user")
        _require_unique_email(session, trimmed, except_user_id=user.id)
        user.email = trimmed
    session.commit()
    session.refresh(user)
    return user


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
