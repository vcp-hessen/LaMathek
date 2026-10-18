from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
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
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        session.commit()


def test_piece_blocked_after_confirm_not_in_draft():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        piece_id = piece.get_json()["id"]

        loan_a = create_loan(client, inv_id, bor_id)
        loan_a_id = loan_a.get_json()["id"]
        assert add_piece_line(client, loan_a_id, piece_id).status_code == 201

        submit_request(client, loan_a_id)
        _login(client, "mgr")
        lines = client.get(f"/api/loans/{loan_a_id}").get_json()["lines"]
        line_ids = [line["id"] for line in lines]
        assert confirm_all_lines(client, loan_a_id, mgr_id, line_ids).status_code == 200

        loan_b = create_loan(client, inv_id, bor_id, groupName="Stamm B")
        assert loan_b.status_code == 201
        loan_b_id = loan_b.get_json()["id"]
        assert add_piece_line(client, loan_b_id, piece_id).status_code == 201
        submit_request(client, loan_b_id)
        _login(client, "mgr")
        lines_b = client.get(f"/api/loans/{loan_b_id}").get_json()["lines"]
        conflict = confirm_all_lines(
            client, loan_b_id, mgr_id, [lines_b[0]["id"]]
        )
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"
    finally:
        tmp.cleanup()


def test_create_loan_allows_second_draft():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        first = create_loan(client, inv_id, bor_id)
        assert first.status_code == 201
        first_id = first.get_json()["id"]
        assert first.get_json()["phase"] == "draft"
        second = create_loan(client, inv_id, bor_id)
        assert second.status_code == 201
        assert second.get_json()["id"] != first_id
        assert second.get_json()["phase"] == "draft"
    finally:
        tmp.cleanup()


def test_draft_does_not_block_second_draft_line():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client, visibility="active")
        bor_id = borrower_id(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        piece_id = piece.get_json()["id"]

        from conftest import login as _login_b

        bor2_id = borrower_id(client, sub="borrower2")
        _login_b(client, "borrower")
        loan_a = create_loan(client, inv_id, bor_id)
        assert loan_a.status_code == 201
        loan_a_id = loan_a.get_json()["id"]
        add_piece_line(client, loan_a_id, piece_id)

        _login_b(client, "borrower2")
        draft_line = client.post(
            f"/api/inventories/{inv_id}/loans/draft-lines",
            json={"pieceId": piece_id, "borrowerUserId": bor2_id},
        )
        assert draft_line.status_code == 201
    finally:
        tmp.cleanup()


def test_workflow_pickup_requires_pack():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        piece_id = piece.get_json()["id"]

        loan = create_loan(client, inv_id, bor_id)
        loan_id = loan.get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        submit_request(client, loan_id)
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        line_ids = [line["id"] for line in lines]
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, line_ids)
        bad = pickup_lines(client, loan_id, line_ids)
        assert bad.status_code == 409
        assert bad.get_json()["error"] == "workflow_step_mismatch"
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, line_ids)
        complete_workflow_step(client, loan_id)
        assert pickup_lines(client, loan_id, line_ids).status_code == 200
    finally:
        tmp.cleanup()


def test_borrower_can_save_wish_dates_on_draft():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        with client.application.app_context():
            session = get_session()
            from lamathek.services.inventories import create_inventory

            inv = create_inventory(session, "Public", visibility="active")
            session.commit()
            inv_id = inv.id

        bor_id = borrower_id(client)
        _login(client, "su")
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]

        _login(client, "borrower")
        patch = client.patch(
            f"/api/loans/{loan_id}",
            json={
                "groupName": "Stamm A",
                "wishPickupOn": "2026-08-01",
                "wishReturnOn": "2026-08-15",
            },
        )
        assert patch.status_code == 200
        body = patch.get_json()
        assert body["wishPickupOn"] == "2026-08-01"
        assert body["wishReturnOn"] == "2026-08-15"
        assert body["pickupOn"] is None
        assert body["returnOn"] is None
    finally:
        tmp.cleanup()


def test_loans_forbidden_without_access():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan = create_loan(client, inv_id, bor_id)
        loan_id = loan.get_json()["id"]

        _login(client, "other", email="other@test.example")
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="other", name="Other", email="other@test.example"
            )
            session.commit()

        forbidden = client.get(f"/api/loans/{loan_id}")
        assert forbidden.status_code == 403
    finally:
        tmp.cleanup()


def test_withdrawn_piece_can_be_added_again():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        other = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Carcassonne"},
        )
        piece_id = piece.get_json()["id"]
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        added = add_piece_line(client, loan_id, piece_id)
        assert added.status_code == 201
        assert add_piece_line(client, loan_id, other.get_json()["id"]).status_code == 201
        line_id = next(
            line["id"]
            for line in client.get(f"/api/loans/{loan_id}").get_json()["lines"]
            if line["pieceId"] == piece_id
        )
        assert submit_request(client, loan_id).status_code == 200
        withdrawn = client.post(
            f"/api/loans/{loan_id}/actions/withdraw",
            json={"lineIds": [line_id]},
        )
        assert withdrawn.status_code == 200
        again = add_piece_line(client, loan_id, piece_id)
        assert again.status_code == 201, again.get_json()
        lines = again.get_json()["lines"]
        revived = next(line for line in lines if line["id"] == line_id)
        assert revived["status"] == "requested"
        assert sum(1 for line in lines if line["pieceId"] == piece_id) == 1
    finally:
        tmp.cleanup()
