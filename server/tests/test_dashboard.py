from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
from loan_helpers import borrower_id, create_loan, setup_inventory, submit_request, add_piece_line


def _bootstrap(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(session, sub="su", name="SU", email=None, force_superuser=True)
        session.commit()


def test_dashboard_lists_own_loan_after_request():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Zelt", "tracking": "piece"},
        )
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt.get_json()["id"], "name": "Z1"},
        )
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        _login(client, "borrower")
        add_piece_line(client, loan_id, piece.get_json()["id"])
        submit_request(client, loan_id)
        dash = client.get("/api/dashboard")
        assert dash.status_code == 200
        mine = dash.get_json()["cards"]["myLoans"]
        assert any(row["id"] == loan_id for row in mine)
    finally:
        tmp.cleanup()
