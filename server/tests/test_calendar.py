from datetime import date, timedelta

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
        upsert_user_from_oidc(session, sub="su", name="SU", email=None, force_superuser=True)
        session.commit()


def test_user_calendar_and_ics():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
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
        line_id = add_piece_line(client, loan_id, piece.get_json()["id"]).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        start = date.today()
        end = start + timedelta(days=3)
        client.patch(
            f"/api/loans/{loan_id}",
            json={"pickupOn": start.isoformat(), "returnOn": end.isoformat()},
        )

        _login(client, "borrower")
        cal = client.get("/api/me/calendar/borrower")
        assert cal.status_code == 200
        items = cal.get_json()["items"]
        assert any(item["loanId"] == loan_id for item in items)
        assert all(item.get("asBorrower") for item in items)

        token = client.post(
            "/api/me/calendar-feeds",
            json={"label": "Handy", "scope": "borrower"},
        )
        assert token.status_code == 201
        path = token.get_json()["path"]
        assert path.startswith("/api/calendar/ics/borrower.ics?token=")
        assert token.get_json()["label"] == "Handy"

        listed = client.get("/api/me/calendar-feeds")
        assert listed.status_code == 200
        assert len(listed.get_json()["items"]) == 1

        feed_id = listed.get_json()["items"][0]["id"]
        deleted = client.delete(f"/api/me/calendar-feeds/{feed_id}")
        assert deleted.status_code == 204

        token = client.post(
            "/api/me/calendar-feeds",
            json={"label": "Handy", "scope": "borrower"},
        )
        path = token.get_json()["path"]
        client.get("/logout")
        feed = client.get(path)
        assert feed.status_code == 200
        assert b"BEGIN:VEVENT" in feed.data
        assert str(loan_id).encode() in feed.data
    finally:
        tmp.cleanup()
