from datetime import date, timedelta

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


def _piece(client, inv_id):
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types",
        json={"name": "Plane", "tracking": "piece"},
    )
    type_id = mt.get_json()["id"]
    piece = client.post(
        f"/api/inventories/{inv_id}/pieces",
        json={"materialTypeId": type_id, "name": "P1"},
    )
    return piece.get_json()["id"]


def test_total_loss_blocks_until_found_again():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        piece_id = _piece(client, inv_id)

        loan_a_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_a_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_a_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_a_id, mgr, [line_id])
        complete_workflow_step(client, loan_a_id)
        pack_lines(client, loan_a_id, [line_id])
        complete_workflow_step(client, loan_a_id)
        pickup_lines(client, loan_a_id, [line_id])
        complete_workflow_step(client, loan_a_id)

        loan_b = create_loan(client, inv_id, bor_id, groupName="B")
        loan_b_id = loan_b.get_json()["id"]
        assert add_piece_line(client, loan_b_id, piece_id).status_code == 201

        _login(client, "mgr")
        client.post(
            f"/api/loans/{loan_a_id}/actions/record-loss",
            json={"entries": [{"lineId": line_id, "reason": "weg"}]},
        )

        _login(client, "borrower")
        submit_request(client, loan_b_id)
        _login(client, "mgr")
        lines_b = client.get(f"/api/loans/{loan_b_id}").get_json()["lines"]
        conflict = confirm_all_lines(client, loan_b_id, mgr, [lines_b[0]["id"]])
        assert conflict.status_code == 409

        found = client.post(
            f"/api/pieces/{piece_id}/found-again",
            json={"reason": "wieder da", "recordedOn": date.today().isoformat()},
        )
        assert found.status_code == 200
        assert found.get_json()["lost"] is False

        conflict2 = confirm_all_lines(client, loan_b_id, mgr, [lines_b[0]["id"]])
        assert conflict2.status_code == 200
    finally:
        tmp.cleanup()

