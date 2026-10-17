from lamathek.db import get_session
from lamathek.services.loan_notifications import get_last_mail_for_tests, set_mail_sender_for_tests
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
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
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        session.commit()


def test_request_mail_to_managers():
    app, tmp = _app_with_db()
    captured: list[dict] = []

    def capture(to, subject, text, html, cc):
        captured.append({"to": to, "cc": cc})

    set_mail_sender_for_tests(capture)
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)

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
        assert captured
        assert any("mgr@test.example" in m["to"] for m in captured)
    finally:
        set_mail_sender_for_tests(None)
        tmp.cleanup()
