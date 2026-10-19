"""Permission rules for global objects and request hardening (Paket 2 of the review)."""

import io
import os
from datetime import date, timedelta

from PIL import Image
from sqlalchemy import select

from conftest import app_with_db, login
from lamathek.db import get_session
from lamathek.models.audit import AUDIT_USER_MERGED, AuditEvent
from lamathek.models.user import User
from lamathek.services.users import upsert_user_from_oidc
from loan_helpers import (
    add_piece_line,
    borrower_id,
    create_loan,
    manager_id,
    setup_inventory,
    submit_request,
)


def _bootstrap(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(session, sub="su", name="su", email="su@x", force_superuser=True)
        session.commit()


def _client():
    app, tmp = app_with_db()
    _bootstrap(app)
    return app, tmp, app.test_client()


def _piece(client, inv_id: int, name: str = "K1") -> int:
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types", json={"name": f"Kohte {name}", "tracking": "piece"}
    )
    assert mt.status_code == 201, mt.get_json()
    piece = client.post(
        f"/api/inventories/{inv_id}/pieces",
        json={"materialTypeId": mt.get_json()["id"], "name": name},
    )
    assert piece.status_code == 201, piece.get_json()
    return piece.get_json()["id"]


def _jpeg(size=(32, 24)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(10, 120, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _second_inventory_manager(client) -> int:
    """Inventar B with its own Materialwart 'mgr_b'."""
    login(client, "su")
    inv = client.post("/api/inventories", json={"name": "Landesbüro", "visibility": "internal"})
    inv_b = inv.get_json()["id"]
    mgr_b = manager_id(client, "mgr_b")
    assert client.put(f"/api/inventories/{inv_b}/permissions", json={"userIds": [mgr_b]}).status_code == 200
    return inv_b


# --- Users ----------------------------------------------------------------------


def test_contact_of_local_user_only_editable_by_managers_of_their_inventory():
    app, tmp, client = _client()
    try:
        inv_a = setup_inventory(client)
        _second_inventory_manager(client)
        login(client, "mgr")
        local = client.post(
            "/api/users", json={"name": "Gast", "phone": "0123", "email": "gast@x.test"}
        ).get_json()
        loan = client.post(
            f"/api/inventories/{inv_a}/loans",
            json={"groupName": "Stamm A", "borrowerUserId": local["id"]},
        )
        assert loan.status_code == 201

        assert client.patch(f"/api/users/{local['id']}", json={"phone": "0456"}).status_code == 200

        login(client, "mgr_b")
        denied = client.patch(f"/api/users/{local['id']}", json={"email": "evil@x.test"})
        assert denied.status_code == 403
        listed = {row["id"]: row for row in client.get("/api/users").get_json()}
        assert listed[local["id"]]["canEditContact"] is False
        assert "phone" not in listed[local["id"]]
        assert all("sub" not in row for row in listed.values())
    finally:
        tmp.cleanup()


def test_login_user_contact_is_theirs_and_superuser_flag_needs_superuser():
    app, tmp, client = _client()
    try:
        setup_inventory(client)
        bor = borrower_id(client)
        login(client, "mgr")
        assert client.patch(f"/api/users/{bor}", json={"email": "x@y.test"}).status_code == 403
        # A denied request changes nothing, even when it also asks for isSuperuser.
        assert (
            client.patch(f"/api/users/{bor}", json={"isSuperuser": True, "phone": "1"}).status_code
            == 403
        )
        with app.app_context():
            user = get_session().get(User, bor)
            assert user.is_superuser is False
            assert user.email == "borrower@test.example"
    finally:
        tmp.cleanup()


def test_merge_is_superuser_only_moves_contact_and_is_audited():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        bor = borrower_id(client)
        login(client, "mgr")
        local = client.post(
            "/api/users", json={"name": "Gast", "phone": "0123", "email": "gast@x.test"}
        ).get_json()
        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm A", "borrowerUserId": local["id"]},
        ).get_json()
        assert (
            client.post(f"/api/users/{local['id']}/merge", json={"targetUserId": bor}).status_code
            == 403
        )
        login(client, "su")
        merged = client.post(f"/api/users/{local['id']}/merge", json={"targetUserId": bor})
        assert merged.status_code == 200, merged.get_json()
        with app.app_context():
            session = get_session()
            event = session.scalar(select(AuditEvent).where(AuditEvent.action == AUDIT_USER_MERGED))
            assert event is not None
            assert event.target_user_id == bor
            assert event.detail == {"mergedUserId": local["id"]}
        assert client.get(f"/api/loans/{loan['id']}").get_json()["borrowerUserId"] == bor
    finally:
        tmp.cleanup()


# --- Inventory permissions ---------------------------------------------------------


def test_grant_upgrades_read_and_local_users_get_no_permission():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        reader = borrower_id(client, "reader")
        mgr = manager_id(client)
        login(client, "su")
        saved = client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mgr], "readerUserIds": [reader]},
        )
        assert saved.status_code == 200
        granted = client.post(f"/api/users/{reader}/inventories", json={"inventoryId": inv_id})
        assert granted.status_code == 200
        assert inv_id in granted.get_json()["inventoryIds"]

        local = client.post(
            "/api/users", json={"name": "Gast", "phone": "0123", "email": "gast@x.test"}
        ).get_json()
        refused = client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mgr], "readerUserIds": [local["id"]]},
        )
        assert refused.status_code == 409
        assert refused.get_json() == {"error": "local_user"}
    finally:
        tmp.cleanup()


# --- Objects ----------------------------------------------------------------------


def test_piece_journal_is_for_materialwarte_only():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client, visibility="active")
        login(client, "mgr")
        piece_id = _piece(client, inv_id)
        assert client.get(f"/api/pieces/{piece_id}/journal").status_code == 200
        borrower_id(client, "reader")
        login(client, "reader")
        assert client.get(f"/api/pieces/{piece_id}").status_code == 200
        assert client.get(f"/api/pieces/{piece_id}/journal").status_code == 403
    finally:
        tmp.cleanup()


def test_loan_photos_visible_to_loan_parties_not_to_inventory_readers(tmp_path):
    os.environ["MEDIA_PATH"] = str(tmp_path / "media")
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client, visibility="active")
        bor = borrower_id(client)
        borrower_id(client, "stranger")
        login(client, "mgr")
        piece_id = _piece(client, inv_id)
        loan_id = create_loan(client, inv_id, bor).get_json()["id"]
        assert add_piece_line(client, loan_id, piece_id).status_code == 201
        assert submit_request(client, loan_id).status_code == 200
        uploaded = client.post(
            f"/api/loans/{loan_id}/photos?role=return",
            data={"file": (io.BytesIO(_jpeg()), "r.jpg", "image/jpeg")},
            content_type="multipart/form-data",
        )
        assert uploaded.status_code == 201, uploaded.get_json()
        photo_id = uploaded.get_json()["id"]

        assert client.get(f"/api/photos/{photo_id}").status_code == 200
        login(client, "stranger")
        assert client.get(f"/api/photos/{photo_id}").status_code == 403
        login(client, "mgr")
        assert client.get(f"/api/photos/{photo_id}").status_code == 200
    finally:
        os.environ.pop("MEDIA_PATH", None)
        tmp.cleanup()


def test_oversized_image_dimensions_are_rejected(tmp_path, monkeypatch):
    os.environ["MEDIA_PATH"] = str(tmp_path / "media")
    from lamathek.services import photo_storage

    monkeypatch.setattr(photo_storage, "MAX_IMAGE_PIXELS", 100)
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        login(client, "mgr")
        piece_id = _piece(client, inv_id)
        response = client.post(
            f"/api/pieces/{piece_id}/photos",
            data={"file": (io.BytesIO(_jpeg((20, 20))), "big.jpg", "image/jpeg")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert response.get_json() == {"error": "image_too_large"}
    finally:
        os.environ.pop("MEDIA_PATH", None)
        tmp.cleanup()


def test_inventory_feed_stops_after_role_is_revoked_and_can_still_be_deleted():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        login(client, "mgr")
        created = client.post(
            "/api/me/calendar-feeds",
            json={"label": "Alle", "scope": "inventory", "inventoryId": inv_id},
        )
        assert created.status_code == 201, created.get_json()
        feed = created.get_json()
        assert client.get(feed["path"]).status_code == 200

        login(client, "su")
        other = manager_id(client, "other")
        assert client.put(
            f"/api/inventories/{inv_id}/permissions", json={"userIds": [other]}
        ).status_code == 200
        assert client.get(feed["path"]).status_code == 404

        login(client, "mgr")
        assert client.delete(f"/api/me/calendar-feeds/{feed['id']}").status_code == 204
    finally:
        tmp.cleanup()


def test_contact_feed_requires_materialwart_role():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client, visibility="active")
        borrower_id(client, "reader")
        login(client, "reader")
        created = client.post(
            "/api/me/calendar-feeds",
            json={"label": "Meine", "scope": "contact", "inventoryId": inv_id},
        )
        assert created.status_code == 403
    finally:
        tmp.cleanup()


# --- Impersonation -------------------------------------------------------------------


def test_impersonation_ends_when_actor_loses_superuser_and_on_new_login():
    app, tmp, client = _client()
    try:
        setup_inventory(client)
        bor = borrower_id(client)
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(session, sub="su2", name="su2", email="su2@x", force_superuser=True)
            session.commit()
        login(client, "su")
        started = client.post("/api/impersonation", json={"userId": bor, "reason": "Support"})
        assert started.status_code == 204
        assert client.get("/api/me").get_json()["id"] == bor

        with app.app_context():
            session = get_session()
            session.scalar(select(User).where(User.oidc_sub == "su")).is_superuser = False
            session.commit()
        me = client.get("/api/me").get_json()
        assert me["sub"] == "su"
        assert me["impersonation"] is None

        with app.app_context():
            session = get_session()
            session.scalar(select(User).where(User.oidc_sub == "su")).is_superuser = True
            session.commit()
        client.post("/api/impersonation", json={"userId": bor, "reason": "Support"})
        app.config["AUTH_DEV_BYPASS"] = True
        app.config["AUTH_DEV_SUB"] = "su2"
        app.config["AUTH_DEV_NAME"] = "su2"
        app.config["AUTH_DEV_EMAIL"] = "su2@x"
        client.get("/login")
        me = client.get("/api/me").get_json()
        assert me["sub"] == "su2"
        assert me["impersonation"] is None
    finally:
        tmp.cleanup()


def test_journal_names_the_superuser_behind_an_impersonated_action():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        bor = borrower_id(client)
        login(client, "mgr")
        piece_id = _piece(client, inv_id)
        loan_id = create_loan(client, inv_id, bor).get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        login(client, "su")
        assert client.post(
            "/api/impersonation", json={"userId": bor, "reason": "Hilfe"}
        ).status_code == 204
        assert submit_request(client, loan_id).status_code == 200
        entries = client.get(f"/api/loans/{loan_id}/journal").get_json()
        step = next(e for e in entries if e["kind"] == "workflow.complete_step")
        assert step["actor"] == {"id": bor, "name": "borrower"}
        assert step["realActor"]["name"] == "su"
    finally:
        tmp.cleanup()


# --- Hardening -----------------------------------------------------------------------


def test_state_changing_api_requests_need_the_csrf_header():
    app, tmp, client = _client()
    try:
        login(client, "su")
        del client.environ_base["HTTP_X_REQUESTED_WITH"]
        forged = client.post("/api/inventories", json={"name": "Forged"})
        assert forged.status_code == 403
        assert forged.get_json() == {"error": "csrf_header_missing"}
        assert client.get("/api/inventories").status_code == 200
    finally:
        tmp.cleanup()


def test_request_body_over_the_limit_is_rejected_as_json():
    app, tmp, client = _client()
    try:
        app.config["MAX_CONTENT_LENGTH"] = 1024
        login(client, "su")
        response = client.post(
            "/api/inventories", data=b"x" * 4096, content_type="application/json"
        )
        assert response.status_code == 413
        assert response.get_json() == {"error": "file_too_large"}
    finally:
        tmp.cleanup()


def test_pdf_download_handles_non_ascii_titles():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        bor = borrower_id(client)
        login(client, "mgr")
        piece_id = _piece(client, inv_id)
        loan_id = create_loan(
            client, inv_id, bor, groupName="Stamm Möwe – Sommer\n\"2026\""
        ).get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        start = date.today() + timedelta(days=3)
        client.post(
            f"/api/loans/{loan_id}/actions/request",
            json={"pickupOn": start.isoformat(), "returnOn": (start + timedelta(days=2)).isoformat()},
        )
        login(client, "mgr")
        mgr = client.get("/api/me").get_json()["id"]
        client.patch(f"/api/loans/{loan_id}", json={"contactUserId": mgr})
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        client.post(f"/api/loans/{loan_id}/actions/confirm", json={"lineIds": [l["id"] for l in lines]})
        client.post(f"/api/loans/{loan_id}/actions/complete-step")
        response = client.get(f"/api/loans/{loan_id}/pdf/pack")
        assert response.status_code == 200
        disposition = response.headers["Content-Disposition"]
        assert disposition.startswith("inline;")
        assert "filename*=UTF-8''" in disposition
        assert "\n" not in disposition
    finally:
        tmp.cleanup()


def test_group_names_are_single_line():
    app, tmp, client = _client()
    try:
        inv_id = setup_inventory(client)
        bor = borrower_id(client)
        created = create_loan(client, inv_id, bor, groupName="Stamm\r\nBcc: x@y   Falke")
        assert created.status_code == 201
        assert created.get_json()["groupName"] == "Stamm Bcc: x@y Falke"
        assert client.post("/api/groups", json={"name": "x"}).status_code in (404, 405)
    finally:
        tmp.cleanup()


def test_public_settings_list_responsible_names_without_email():
    app, tmp, client = _client()
    try:
        setup_inventory(client)
        anonymous = app.test_client()
        body = anonymous.get("/api/settings").get_json()
        assert body["contentResponsible"] == "mgr"
        assert "@" not in body["contentResponsible"]
    finally:
        tmp.cleanup()
