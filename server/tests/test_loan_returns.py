from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
from loan_helpers import (
    add_piece_line,
    borrower_id,
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


def test_restock_closes_line():
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
        piece_id = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt.get_json()["id"], "name": "Catan"},
        ).get_json()["id"]

        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        submit_request(client, loan_id)
        _login(client, "mgr")
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        line_ids = [line["id"] for line in lines]
        confirm_all_lines(client, loan_id, mgr_id, line_ids)
        pack_lines(client, loan_id, line_ids)
        pickup_lines(client, loan_id, line_ids)
        client.post(
            f"/api/loans/{loan_id}/actions/report-return",
            json={"lineIds": line_ids},
        )
        restock = client.post(
            f"/api/loans/{loan_id}/actions/restock",
            json={"lineIds": line_ids},
        )
        assert restock.status_code == 200
        detail = restock.get_json()
        assert detail["lines"][0]["status"] == "restocked"
        assert detail["phase"] == "closed"
    finally:
        tmp.cleanup()
