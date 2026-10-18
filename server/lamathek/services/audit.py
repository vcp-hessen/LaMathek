from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lamathek.models.audit import (
    AUDIT_IMPERSONATION_ENDED,
    AUDIT_IMPERSONATION_STARTED,
    AUDIT_INSTALLATION_SETTINGS_UPDATED,
    AuditEvent,
)
from lamathek.models.settings import InstallationSettings
from lamathek.models.user import User

INSTALLATION_SETTINGS_AUDIT_FIELDS: tuple[tuple[str, str], ...] = (
    ("title", "title"),
    ("subtitle", "subtitle"),
    ("legal_name", "legalName"),
    ("legal_address", "legalAddress"),
    ("email", "email"),
    ("website", "website"),
    ("phone", "phone"),
    ("represented_by", "representedBy"),
    ("register", "register"),
    ("map_latitude", "mapLatitude"),
    ("map_longitude", "mapLongitude"),
    ("host_name", "hostName"),
    ("host_address", "hostAddress"),
    ("host_privacy_url", "hostPrivacyUrl"),
    ("auth_provider_name", "authProviderName"),
    ("auth_provider_same_host", "authProviderSameHost"),
    ("authority_name", "authorityName"),
    ("authority_url", "authorityUrl"),
    ("calendar_bundesland", "calendarBundesland"),
)


def record_audit_event(
    session: Session,
    *,
    actor_user_id: int,
    action: str,
    target_user_id: int | None = None,
    reason: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        target_user_id=target_user_id,
        reason=reason,
        detail=detail,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_audit_events(session: Session, *, limit: int = 200) -> list[AuditEvent]:
    return list(
        session.scalars(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        ).all()
    )


def installation_settings_audit_values(settings: InstallationSettings) -> dict[str, Any]:
    return {
        json_key: getattr(settings, attr)
        for attr, json_key in INSTALLATION_SETTINGS_AUDIT_FIELDS
    }


def diff_installation_settings(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for key in before:
        old = before[key]
        new = after[key]
        if old != new:
            changes[key] = {"old": old, "new": new}
    return changes


def log_installation_settings_update(
    session: Session,
    *,
    actor: User,
    before_values: dict[str, Any],
    after: InstallationSettings,
) -> AuditEvent | None:
    new_values = installation_settings_audit_values(after)
    changes = diff_installation_settings(before_values, new_values)
    if not changes:
        return None
    return record_audit_event(
        session,
        actor_user_id=actor.id,
        action=AUDIT_INSTALLATION_SETTINGS_UPDATED,
        detail={"changes": changes},
    )


def log_impersonation_started(
    session: Session,
    *,
    actor: User,
    target: User,
    reason: str,
) -> AuditEvent:
    return record_audit_event(
        session,
        actor_user_id=actor.id,
        action=AUDIT_IMPERSONATION_STARTED,
        target_user_id=target.id,
        reason=reason,
    )


def log_impersonation_ended(
    session: Session,
    *,
    actor: User,
    target: User | None,
) -> AuditEvent:
    return record_audit_event(
        session,
        actor_user_id=actor.id,
        action=AUDIT_IMPERSONATION_ENDED,
        target_user_id=target.id if target is not None else None,
    )
