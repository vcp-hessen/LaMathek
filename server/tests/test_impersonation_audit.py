from lamathek.db import get_session
from lamathek.models.audit import (
    AUDIT_IMPERSONATION_ENDED,
    AUDIT_IMPERSONATION_STARTED,
    AUDIT_INSTALLATION_SETTINGS_UPDATED,
    AuditEvent,
)
from lamathek.services.inventories import grant_inventory_permission
from lamathek.services.users import upsert_user_from_oidc
from sqlalchemy import select

from conftest import app_with_db as _app_with_db, login as _login

_SETTINGS_PATCH = {
    "title": "Neu",
    "subtitle": "Untertitel",
    "legalName": "Anbieter GmbH",
    "legalAddress": "",
    "email": "",
    "website": "",
    "phone": "",
    "representedBy": "",
    "register": "",
    "mapLatitude": 50.65,
    "mapLongitude": 9.16,
    "hostName": "",
    "hostAddress": "",
    "hostPrivacyUrl": "",
    "authProviderName": "",
    "authProviderSameHost": False,
    "authorityName": "",
    "authorityUrl": "",
}


def _seed_users(session):
    su = upsert_user_from_oidc(
        session, sub="su", name="Super", email="su@example.com", force_superuser=True
    )
    person = upsert_user_from_oidc(
        session,
        sub="person",
        name="Person",
        email="person@example.com",
        force_superuser=False,
    )
    other_su = upsert_user_from_oidc(
        session,
        sub="su2",
        name="Other SU",
        email="su2@example.com",
        force_superuser=True,
    )
    return su, person, other_su


def test_impersonation_requires_reason_and_grants_target_permissions():
    app, tmp = _app_with_db()
    with app.app_context():
        session = get_session()
        su, person, _other_su = _seed_users(session)
        from lamathek.services.inventories import create_inventory

        create_inventory(session, name="Test")
        su_id = su.id
        person_id = person.id

    client = app.test_client()
    _login(client, "su")

    missing_reason = client.post(
        "/api/impersonation", json={"userId": person_id, "reason": "  "}
    )
    assert missing_reason.status_code == 400
    assert missing_reason.get_json()["error"] == "invalid_reason"

    start = client.post(
        "/api/impersonation",
        json={"userId": person_id, "reason": "Support-Anfrage"},
    )
    assert start.status_code == 204

    me = client.get("/api/me")
    assert me.status_code == 200
    body = me.get_json()
    assert body["id"] == person_id
    assert body["isSuperuser"] is False
    assert body["impersonation"]["reason"] == "Support-Anfrage"
    assert body["impersonation"]["actor"]["sub"] == "su"

    users_list = client.get("/api/users")
    assert users_list.status_code == 403

    stop = client.delete("/api/impersonation")
    assert stop.status_code == 204

    me_after = client.get("/api/me")
    assert me_after.get_json()["id"] == su_id
    assert me_after.get_json()["impersonation"] is None

    with app.app_context():
        events = list(get_session().scalars(select(AuditEvent)).all())
        actions = [e.action for e in events]
        assert AUDIT_IMPERSONATION_STARTED in actions
        assert AUDIT_IMPERSONATION_ENDED in actions

    tmp.cleanup()


def test_cannot_impersonate_superuser_or_self():
    app, tmp = _app_with_db()
    with app.app_context():
        session = get_session()
        su, person, other_su = _seed_users(session)
        su_id = su.id
        person_id = person.id
        other_su_id = other_su.id

    client = app.test_client()
    _login(client, "su")

    self_resp = client.post(
        "/api/impersonation", json={"userId": su_id, "reason": "test"}
    )
    assert self_resp.status_code == 400
    assert self_resp.get_json()["error"] == "cannot_impersonate_self"

    su_resp = client.post(
        "/api/impersonation", json={"userId": other_su_id, "reason": "test"}
    )
    assert su_resp.status_code == 400
    assert su_resp.get_json()["error"] == "cannot_impersonate_superuser"

    ok = client.post(
        "/api/impersonation", json={"userId": person_id, "reason": "ok"}
    )
    assert ok.status_code == 204

    active = client.post(
        "/api/impersonation", json={"userId": person_id, "reason": "again"}
    )
    assert active.status_code == 400
    assert active.get_json()["error"] == "impersonation_active"

    tmp.cleanup()


def test_logout_ends_impersonation_with_audit():
    app, tmp = _app_with_db()
    with app.app_context():
        session = get_session()
        _su, person, _other_su = _seed_users(session)
        person_id = person.id

    client = app.test_client()
    _login(client, "su")
    client.post("/api/impersonation", json={"userId": person_id, "reason": "logout test"})

    logout = client.post("/logout")
    assert logout.status_code == 204

    with app.app_context():
        events = list(
            get_session().scalars(
                select(AuditEvent).where(AuditEvent.action == AUDIT_IMPERSONATION_ENDED)
            ).all()
        )
        assert len(events) == 1

    tmp.cleanup()


def test_settings_patch_writes_audit_only_for_changes():
    app, tmp = _app_with_db()
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session, sub="su", name="Super", email=None, force_superuser=True
        )

    client = app.test_client()
    _login(client, "su")

    patch = client.patch("/api/settings", json=_SETTINGS_PATCH)
    assert patch.status_code == 200

    with app.app_context():
        events = list(
            get_session().scalars(
                select(AuditEvent).where(
                    AuditEvent.action == AUDIT_INSTALLATION_SETTINGS_UPDATED
                )
            ).all()
        )
        assert len(events) == 1
        changes = events[0].detail["changes"]
        assert "title" in changes
        assert changes["title"]["new"] == "Neu"

    noop = client.patch("/api/settings", json=_SETTINGS_PATCH)
    assert noop.status_code == 200

    with app.app_context():
        count = len(
            list(
                get_session().scalars(
                    select(AuditEvent).where(
                        AuditEvent.action == AUDIT_INSTALLATION_SETTINGS_UPDATED
                    )
                ).all()
            )
        )
        assert count == 1

    tmp.cleanup()


def test_audit_events_superuser_only():
    app, tmp = _app_with_db()
    with app.app_context():
        session = get_session()
        _su, person, _other_su = _seed_users(session)
        person_id = person.id

    client = app.test_client()
    _login(client, "su")
    as_su = client.get("/api/audit-events")
    assert as_su.status_code == 200

    client.post("/api/impersonation", json={"userId": person_id, "reason": "audit"})
    as_target = client.get("/api/audit-events")
    assert as_target.status_code == 403

    tmp.cleanup()
