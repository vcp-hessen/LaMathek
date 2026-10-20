from conftest import app_with_db as _app_with_db, login as _login
from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc
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
    _login(client, "su")
    piece_id = _piece(client, inv_id)
    loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
    add_piece_line(client, loan_id, piece_id)
    detail = client.get(f"/api/loans/{loan_id}").get_json()
    line_id = detail["lines"][0]["id"]
    return loan_id, line_id


def test_delete_unreleased_loan_as_borrower():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id, _ = _loan_with_line(client, inv_id, bor_id)

        _login(client, "borrower")
        res = client.delete(f"/api/loans/{loan_id}")
        assert res.status_code == 204
        assert client.get(f"/api/loans/{loan_id}").status_code == 404
    finally:
        tmp.cleanup()


def test_delete_unreleased_forbidden_for_manager():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id, _ = _loan_with_line(client, inv_id, bor_id)

        _login(client, "mgr")
        res = client.delete(f"/api/loans/{loan_id}")
        assert res.status_code == 403
    finally:
        tmp.cleanup()


def test_superuser_can_delete_loan_in_review():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)
        submit_request(client, loan_id)

        _login(client, "su")
        res = client.delete(f"/api/loans/{loan_id}")
        assert res.status_code == 204
        assert client.get(f"/api/loans/{loan_id}").status_code == 404
    finally:
        tmp.cleanup()


def test_delete_blocked_after_confirm():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)

        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, [line_id])

        _login(client, "borrower")
        res = client.delete(f"/api/loans/{loan_id}")
        assert res.status_code == 409
        assert res.get_json()["error"] == "invalid_loan_state"
    finally:
        tmp.cleanup()


def test_cancel_unpacked_loan():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)

        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, [line_id])

        _login(client, "borrower")
        res = client.post(f"/api/loans/{loan_id}/actions/cancel")
        assert res.status_code == 200
        detail = res.get_json()
        assert detail["phase"] == "closed"
        assert detail["lines"][0]["status"] == "withdrawn"
    finally:
        tmp.cleanup()


def test_cancel_blocked_when_packed():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)

        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])

        _login(client, "borrower")
        res = client.post(f"/api/loans/{loan_id}/actions/cancel")
        assert res.status_code == 409
        assert res.get_json()["error"] == "invalid_loan_state"
    finally:
        tmp.cleanup()


def test_skip_pickup_to_return():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)

        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)

        _login(client, "borrower")
        res = client.post(f"/api/loans/{loan_id}/actions/skip-pickup")
        assert res.status_code == 200
        assert res.get_json()["lines"][0]["status"] == "return_reported"
    finally:
        tmp.cleanup()


def test_skip_pickup_blocked_with_open_confirmed():
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
        p1 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "A"},
        ).get_json()["id"]
        p2 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "B"},
        ).get_json()["id"]

        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        add_piece_line(client, loan_id, p1)
        add_piece_line(client, loan_id, p2)
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        line_a, line_b = lines[0]["id"], lines[1]["id"]

        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, [line_a, line_b])
        pack_lines(client, loan_id, [line_a])

        _login(client, "borrower")
        res = client.post(f"/api/loans/{loan_id}/actions/skip-pickup")
        assert res.status_code == 409
        assert res.get_json()["error"] in ("invalid_loan_state", "workflow_step_mismatch")
    finally:
        tmp.cleanup()


def test_skip_pickup_blocked_after_pickup():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        loan_id, line_id = _loan_with_line(client, inv_id, bor_id)

        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr_id, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        pickup_lines(client, loan_id, [line_id])

        _login(client, "borrower")
        res = client.post(f"/api/loans/{loan_id}/actions/skip-pickup")
        assert res.status_code == 409
        assert res.get_json()["error"] in ("invalid_loan_state", "workflow_step_mismatch")
    finally:
        tmp.cleanup()
