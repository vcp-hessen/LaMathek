from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
from loan_helpers import (
    add_piece_line,
    borrower_id,
    confirm_all_lines,
    create_loan,
    manager_id,
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


def test_permanent_loan_no_return_date():
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

        loan = create_loan(client, inv_id, bor_id, kind="permanent")
        loan_id = loan.get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        from datetime import date, timedelta

        start = date.today() + timedelta(days=3)
        req = client.post(
            f"/api/loans/{loan_id}/actions/request",
            json={"pickupOn": start.isoformat()},
        )
        assert req.status_code == 200
        assert req.get_json()["returnOn"] is None
        _login(client, "mgr")
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        confirm = confirm_all_lines(client, loan_id, mgr_id, [lines[0]["id"]])
        assert confirm.status_code == 200
    finally:
        tmp.cleanup()
