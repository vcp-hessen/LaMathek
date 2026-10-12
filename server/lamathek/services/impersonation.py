from datetime import datetime, timezone

from flask import session
from sqlalchemy.orm import Session

from lamathek.auth import session_actor_sub, session_impersonation
from lamathek.models.user import User
from lamathek.services.audit import log_impersonation_ended, log_impersonation_started
from lamathek.services.users import user_by_id, user_by_oidc_sub


class ImpersonationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def start_impersonation(
    session_db: Session,
    *,
    actor: User,
    target_user_id: int,
    reason: str,
) -> User:
    if not actor.is_superuser:
        raise ImpersonationError("forbidden")
    if session_impersonation() is not None:
        raise ImpersonationError("impersonation_active")

    trimmed = reason.strip()
    if not trimmed:
        raise ImpersonationError("invalid_reason")

    target = user_by_id(session_db, target_user_id)
    if target is None:
        raise ImpersonationError("invalid_target")
    if target.id == actor.id:
        raise ImpersonationError("cannot_impersonate_self")
    if target.is_superuser:
        raise ImpersonationError("cannot_impersonate_superuser")

    started_at = datetime.now(timezone.utc).isoformat()
    session["impersonation"] = {
        "sub": target.oidc_sub,
        "reason": trimmed,
        "startedAt": started_at,
    }
    log_impersonation_started(
        session_db, actor=actor, target=target, reason=trimmed
    )
    return target


def stop_impersonation(session_db: Session, *, actor: User) -> None:
    imp = session_impersonation()
    if imp is None:
        raise ImpersonationError("not_impersonating")

    target_sub = imp.get("sub")
    target = user_by_oidc_sub(session_db, target_sub) if target_sub else None
    session.pop("impersonation", None)
    log_impersonation_ended(session_db, actor=actor, target=target)


def end_impersonation_if_active(session_db: Session, *, actor: User) -> None:
    if session_impersonation() is None:
        return
    stop_impersonation(session_db, actor=actor)


def actor_user_from_session(session_db: Session) -> User | None:
    sub = session_actor_sub()
    if not sub:
        return None
    return user_by_oidc_sub(session_db, sub)
