from datetime import date, timedelta

from conftest import app_with_db as _app_with_db, login as _login
from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc, user_by_id
from loan_helpers import (
    add_piece_line,
    borrower_id,
    complete_workflow_step,
    confirm_all_lines,
    create_loan,
    manager_id,
    pack_lines,
    pickup_lines,
    setup_inventory,
    submit_request,
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
        json={"materialTypeId": type_id, "name": "Catan"},
    )
    return piece.get_json()["id"]


def _loan_with_line(client, inv_id: int, bor_id: int) -> tuple[int, int]:
    _login(client, "borrower")
    loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
    _login(client, "su")
    piece_id = _piece(client, inv_id)
    _login(client, "borrower")
    add_piece_line(client, loan_id, piece_id)
    detail = client.get(f"/api/loans/{loan_id}").get_json()
    return loan_id, detail["lines"][0]["id"]


def _dates():
    start = date.today() + timedelta(days=3)
    return start, start + timedelta(days=4)


def test_manager_cannot_see_foreign_draft():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id, _ = _loan_with_line(client, inv_id, bor_id)

        _login(client, "mgr")
        listed = client.get(f"/api/inventories/{inv_id}/loans").get_json()
        assert all(row["id"] != loan_id for row in listed)
        assert client.get(f"/api/loans/{loan_id}").status_code == 403
        draft = client.get(
            f"/api/inventories/{inv_id}/loans/draft",
            query_string={"borrowerUserId": bor_id},
        )
        assert draft.status_code == 403
    finally:
        tmp.cleanup()


def test_create_for_other_starts_active_with_manager_as_contact():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        pickup, end = _dates()
        _login(client, "mgr")
        created = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={
                "groupName": "Stamm B",
                "borrowerUserId": bor_id,
                "pickupOn": pickup.isoformat(),
                "returnOn": end.isoformat(),
            },
        )
        assert created.status_code == 201
        body = created.get_json()
        assert body["phase"] == "draft"
        assert body["contactUserId"] == mgr
        assert body["wishPickupOn"] == pickup.isoformat()

        _login(client, "borrower")
        seen = client.get(f"/api/loans/{body['id']}")
        assert seen.status_code == 200
        assert seen.get_json()["phase"] == "draft"
    finally:
        tmp.cleanup()


def test_pickup_and_return_for_borrower_and_manager_not_stranger():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        borrower_id(client, "stranger")
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)

        _login(client, "borrower")
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)

        _login(client, "stranger")
        assert pickup_lines(client, loan_id, [line_id]).status_code == 403

        _login(client, "borrower")
        picked = pickup_lines(client, loan_id, [line_id])
        assert picked.status_code == 200
        complete_workflow_step(client, loan_id)

        _login(client, "stranger")
        reported = client.post(
            f"/api/loans/{loan_id}/actions/report-return",
            json={"lineIds": [line_id]},
        )
        assert reported.status_code == 403

        _login(client, "mgr")
        reported = client.post(
            f"/api/loans/{loan_id}/actions/report-return",
            json={"lineIds": [line_id]},
        )
        assert reported.status_code == 200
    finally:
        tmp.cleanup()


def test_wish_dates_frozen_after_request():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id, _ = _loan_with_line(client, inv_id, bor_id)
        _login(client, "borrower")
        assert submit_request(client, loan_id).status_code == 200
        later = (date.today() + timedelta(days=20)).isoformat()
        patched = client.patch(
            f"/api/loans/{loan_id}",
            json={"wishPickupOn": later},
        )
        assert patched.status_code == 409
        assert patched.get_json()["error"] == "invalid_loan_state"
    finally:
        tmp.cleanup()


def test_read_grant_lists_internal_inventory_and_allows_own_loan():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        reader = borrower_id(client, "reader")
        outsider = borrower_id(client, "outsider")
        mgr = manager_id(client)
        _login(client, "su")
        perm = client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mgr], "readerUserIds": [reader]},
        )
        assert perm.status_code == 200
        assert reader in perm.get_json()["readerUserIds"]

        _login(client, "reader")
        listed = client.get("/api/inventories").get_json()
        row = next(item for item in listed if item["id"] == inv_id)
        assert row["canManage"] is False
        created = create_loan(client, inv_id, reader)
        assert created.status_code == 201
        assert created.get_json()["phase"] == "draft"

        _login(client, "outsider")
        assert client.get(f"/api/inventories/{inv_id}").status_code == 403
        denied = create_loan(client, inv_id, outsider, grant_read=False)
        assert denied.status_code == 403
    finally:
        tmp.cleanup()


def test_local_user_has_no_oidc_login_and_can_borrow():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        mgr = manager_id(client)
        _login(client, "mgr")
        created_user = client.post(
            "/api/users",
            json={"name": "Ohne Konto", "phone": "+491511234567", "email": "ohne@example.test"},
        )
        assert created_user.status_code == 201
        body = created_user.get_json()
        assert body["hasLogin"] is False
        assert "sub" not in body
        assert body["name"] == "Ohne Konto"
        local_id = body["id"]

        pickup, end = _dates()
        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={
                "groupName": "Stamm C",
                "borrowerUserId": local_id,
                "pickupOn": pickup.isoformat(),
                "returnOn": end.isoformat(),
            },
        )
        assert loan.status_code == 201
        assert loan.get_json()["borrowerUserId"] == local_id
        assert loan.get_json()["contactUserId"] == mgr

        with app.app_context():
            stored = user_by_id(get_session(), local_id)
            assert stored is not None
            assert stored.oidc_sub.startswith("local:")
    finally:
        tmp.cleanup()
