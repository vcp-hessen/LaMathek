from conftest import app_with_db as _app_with_db, login as _login
from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc
from loan_helpers import (
    add_piece_line,
    borrower_id,
    create_loan,
    manager_id,
    setup_inventory,
)


def _bootstrap(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(session, sub="su", name="SU", email=None, force_superuser=True)
        session.commit()


def _piece(client, inv_id: int) -> int:
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types",
        json={"name": "Brettspiel", "tracking": "piece"},
    )
    type_id = mt.get_json()["id"]
    piece = client.post(
        f"/api/inventories/{inv_id}/pieces",
        json={"materialTypeId": type_id, "name": "Spiel"},
    )
    return piece.get_json()["id"]


def test_create_for_other_is_active_without_dates_and_listed():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        _login(client, "mgr")
        created = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "—", "borrowerUserId": bor_id, "kind": "short"},
        )
        assert created.status_code == 201, created.get_json()
        body = created.get_json()
        assert body["phase"] == "draft"
        assert body["contactUserId"] == mgr
        assert body["pickupOn"] is None
        listed = client.get(f"/api/inventories/{inv_id}/loans")
        assert listed.status_code == 200
        assert body["id"] in [row["id"] for row in listed.get_json()]
    finally:
        tmp.cleanup()


def test_changing_borrower_on_own_draft_promotes_it():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        created = create_loan(client, inv_id, mgr)
        assert created.status_code == 201
        loan_id = created.get_json()["id"]
        assert created.get_json()["phase"] == "draft"
        _login(client, "su")
        piece_id = _piece(client, inv_id)
        _login(client, "mgr")
        line = add_piece_line(client, loan_id, piece_id)
        assert line.status_code == 201, line.get_json()
        patched = client.patch(
            f"/api/loans/{loan_id}",
            json={"borrowerUserId": bor_id},
        )
        assert patched.status_code == 200, patched.get_json()
        body = patched.get_json()
        assert body["phase"] == "review"
        assert body["borrowerUserId"] == bor_id
        assert body["contactUserId"] == mgr
        assert body["lines"][0]["status"] == "requested"
        listed = client.get(f"/api/inventories/{inv_id}/loans")
        assert body["id"] in [row["id"] for row in listed.get_json()]
    finally:
        tmp.cleanup()


def test_merge_rewrites_loans_and_deletes_placeholder():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        _login(client, "mgr")
        created_user = client.post(
            "/api/users",
            json={"name": "Gast", "phone": "0123", "email": "gast@example.test"},
        )
        assert created_user.status_code == 201, created_user.get_json()
        placeholder = created_user.get_json()
        assert placeholder["hasLogin"] is False
        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "—", "borrowerUserId": placeholder["id"]},
        )
        assert loan.status_code == 201, loan.get_json()
        loan_id = loan.get_json()["id"]
        merged = client.post(
            f"/api/users/{placeholder['id']}/merge",
            json={"targetUserId": bor_id},
        )
        assert merged.status_code == 200, merged.get_json()
        assert merged.get_json()["id"] == bor_id
        detail = client.get(f"/api/loans/{loan_id}")
        assert detail.get_json()["borrowerUserId"] == bor_id
        listed = client.get("/api/users")
        assert placeholder["id"] not in [row["id"] for row in listed.get_json()]
    finally:
        tmp.cleanup()


def test_manager_sets_group_and_title_on_loan_for_other():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        _login(client, "mgr")
        created = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "—", "borrowerUserId": bor_id, "kind": "short"},
        )
        assert created.status_code == 201
        loan_id = created.get_json()["id"]
        patched = client.patch(
            f"/api/loans/{loan_id}",
            json={"groupName": "Stamm B", "eventName": "Sommerlager", "kind": "short"},
        )
        assert patched.status_code == 200, patched.get_json()
        body = patched.get_json()
        assert body["groupName"] == "Stamm B"
        assert body["eventName"] == "Sommerlager"
        _login(client, "borrower")
        denied = client.patch(
            f"/api/loans/{loan_id}",
            json={"pickupOn": "2026-10-25"},
        )
        assert denied.status_code == 403
    finally:
        tmp.cleanup()


def test_phone_lives_on_the_user_and_can_be_changed():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        _login(client, "mgr")
        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "—", "borrowerUserId": bor_id},
        )
        assert loan.status_code == 201
        loan_id = loan.get_json()["id"]
        assert loan.get_json()["borrowerPhone"] == "+491234567890"
        patched = client.patch(
            f"/api/users/{bor_id}",
            json={"phone": "0999", "email": "borrower@test.example"},
        )
        assert patched.status_code == 200, patched.get_json()
        detail = client.get(f"/api/loans/{loan_id}")
        assert detail.get_json()["borrowerPhone"] == "0999"
        missing = client.post(
            "/api/users",
            json={"name": "Gast", "phone": "0123"},
        )
        assert missing.status_code == 400
    finally:
        tmp.cleanup()


def test_local_user_cannot_receive_inventory_permission_or_be_contact():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        _login(client, "mgr")
        created_user = client.post(
            "/api/users",
            json={"name": "Gast", "phone": "0123", "email": "gast@example.test"},
        )
        placeholder_id = created_user.get_json()["id"]
        _login(client, "su")
        granted = client.post(
            f"/api/users/{placeholder_id}/inventories",
            json={"inventoryId": inv_id},
        )
        assert granted.status_code == 409
        assert granted.get_json()["error"] == "local_user"
        _login(client, "mgr")
        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "—", "borrowerUserId": borrower_id(client)},
        )
        loan_id = loan.get_json()["id"]
        contact = client.patch(
            f"/api/loans/{loan_id}",
            json={"contactUserId": placeholder_id},
        )
        assert contact.status_code == 400
        assert contact.get_json()["error"] == "invalid_contact"
    finally:
        tmp.cleanup()
