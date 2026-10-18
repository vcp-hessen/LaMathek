from datetime import date, timedelta

from lamathek.db import get_session
from lamathek.i18n import resolve_locale, t
from lamathek.services.loan_notifications import set_mail_sender_for_tests
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


def _mail_to(captured, address: str) -> dict | None:
    for mail in captured:
        if mail["to"] == address:
            return mail
    return None


def test_request_mail_to_managers():
    app, tmp = _app_with_db()
    captured: list[dict] = []

    def capture(to, subject, text, html, cc, attachments=None):
        captured.append({"to": to, "cc": cc, "attachments": attachments})

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

        second = manager_id(client, "mgr2")
        _login(client, "su")
        saved = client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [manager_id(client), second]},
        )
        assert saved.status_code == 200

        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        submit_request(client, loan_id)
        assert len(captured) == 2

        mgr_mail = _mail_to(captured, "mgr@test.example")
        assert mgr_mail is not None
        assert "mgr2@test.example" in mgr_mail["cc"]
        assert "borrower@test.example" not in mgr_mail["cc"]

        bor_mail = _mail_to(captured, "borrower@test.example")
        assert bor_mail is not None
        assert bor_mail["cc"] == []
    finally:
        set_mail_sender_for_tests(None)
        tmp.cleanup()


def test_request_mail_is_german_and_addressed():
    app, tmp = _app_with_db()
    captured: list[dict] = []

    def capture(to, subject, text, html, cc, attachments=None):
        captured.append(
            {"to": to, "subject": subject, "text": text, "html": html, "cc": cc}
        )

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

        pickup = (date.today() + timedelta(days=7)).strftime("%d.%m.%Y")
        assert len(captured) == 2

        mgr_mail = _mail_to(captured, "mgr@test.example")
        assert mgr_mail is not None
        assert "borrower@test.example" not in mgr_mail["cc"]
        assert mgr_mail["subject"].startswith("[Donnerskopf] ")
        assert "Neue Anfrage von borrower" in mgr_mail["subject"]
        assert "Stamm A" in mgr_mail["subject"]
        assert "request" not in mgr_mail["subject"]
        assert "Catan" in mgr_mail["text"]
        assert pickup in mgr_mail["text"]
        assert "sage zu oder lehne ab" in mgr_mail["text"]
        assert "Neue Anfrage" in mgr_mail["text"]
        assert f"/inventories/{inv_id}/loans/{loan_id}" in mgr_mail["html"]

        bor_mail = _mail_to(captured, "borrower@test.example")
        assert bor_mail is not None
        assert "Anfrage unterwegs" in bor_mail["text"]
        assert bor_mail["text"] != mgr_mail["text"]
    finally:
        set_mail_sender_for_tests(None)
        tmp.cleanup()


def test_complete_step_sends_role_specific_mails():
    app, tmp = _app_with_db()
    captured: list[dict] = []

    def capture(to, subject, text, html, cc, attachments=None):
        captured.append({"to": to, "subject": subject, "text": text, "cc": cc})

    set_mail_sender_for_tests(capture)
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
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        captured.clear()
        _login(client, "mgr")
        patched = client.patch(
            f"/api/loans/{loan_id}",
            json={"contactUserId": mgr_id},
        )
        assert patched.status_code == 200
        blocked = client.post(f"/api/loans/{loan_id}/actions/complete-step")
        assert blocked.status_code == 409
        assert blocked.get_json()["error"] == "step_incomplete"
        assert captured == []
        confirmed = client.post(
            f"/api/loans/{loan_id}/actions/confirm",
            json={"lineIds": [line_id]},
        )
        assert confirmed.status_code == 200
        assert captured == []
        done = client.post(f"/api/loans/{loan_id}/actions/complete-step")
        assert done.status_code == 200
        assert done.get_json()["lines"][0]["status"] == "confirmed"
        assert done.get_json()["hasPendingMailChanges"] is False
        assert done.get_json()["phase"] == "pack"
        assert len(captured) == 2

        bor_mail = _mail_to(captured, "borrower@test.example")
        assert bor_mail is not None
        assert bor_mail["cc"] == []
        assert bor_mail["subject"].startswith("[Donnerskopf] ")
        assert "Zusage" in bor_mail["subject"]
        assert "Material ist zugesagt" in bor_mail["text"]
        assert "Catan" in bor_mail["text"]
        assert "Bestätigt" in bor_mail["text"]
        assert "Bitte packe" not in bor_mail["text"]

        mgr_mail = _mail_to(captured, "mgr@test.example")
        assert mgr_mail is not None
        assert "Freigabe erledigt" in mgr_mail["subject"]
        assert "Jetzt packen" in mgr_mail["text"]
        assert "Bitte packe" in mgr_mail["text"]
        assert bor_mail["text"] != mgr_mail["text"]
    finally:
        set_mail_sender_for_tests(None)
        tmp.cleanup()


def test_quiet_line_change_is_listed_in_the_step_mail():
    app, tmp = _app_with_db()
    captured: list[dict] = []

    def capture(to, subject, text, html, cc, attachments=None):
        captured.append({"to": to, "text": text})

    set_mail_sender_for_tests(capture)
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        ).get_json()["id"]
        first = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt, "name": "Catan"},
        ).get_json()["id"]
        second = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt, "name": "Carcassonne"},
        ).get_json()["id"]
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        add_piece_line(client, loan_id, first)
        added = add_piece_line(client, loan_id, second).get_json()["lines"]
        quiet_id = next(line["id"] for line in added if line["pieceId"] == first)
        submit_request(client, loan_id)
        captured.clear()
        _login(client, "mgr")
        patched = client.patch(
            f"/api/loans/{loan_id}",
            json={"contactUserId": mgr_id},
        )
        assert patched.status_code == 200
        confirmed = client.post(
            f"/api/loans/{loan_id}/actions/confirm",
            json={"lineIds": [quiet_id]},
        )
        assert confirmed.status_code == 200, confirmed.get_json()
        assert captured == []
        assert confirmed.get_json()["hasPendingMailChanges"] is True
        assert confirmed.get_json()["phase"] == "review"
        blocked = client.post(f"/api/loans/{loan_id}/actions/complete-step")
        assert blocked.status_code == 409
        assert captured == []
        other_id = next(line["id"] for line in confirmed.get_json()["lines"] if line["id"] != quiet_id)
        second = client.post(
            f"/api/loans/{loan_id}/actions/confirm",
            json={"lineIds": [other_id]},
        )
        assert second.status_code == 200
        done = client.post(f"/api/loans/{loan_id}/actions/complete-step")
        assert done.status_code == 200, done.get_json()
        body = done.get_json()
        assert body["hasPendingMailChanges"] is False
        assert body["phase"] == "pack"
        assert {line["status"] for line in body["lines"]} == {"confirmed"}
        assert len(captured) == 2
        for mail in captured:
            assert "Carcassonne" in mail["text"]
            assert "Catan" in mail["text"]
    finally:
        set_mail_sender_for_tests(None)
        tmp.cleanup()


def test_mail_partial_failure_retries_without_duplicate():
    app, tmp = _app_with_db()
    sent_to: list[str] = []

    def flaky(to, subject, text, html, cc, attachments=None):
        del subject, text, html, cc
        sent_to.append(to)
        if len(sent_to) == 2:
            raise RuntimeError("smtp down")

    set_mail_sender_for_tests(flaky)
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)
        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        ).get_json()["id"]
        piece_id = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt, "name": "Catan"},
        ).get_json()["id"]
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        submit_request(client, loan_id)
        sent_to.clear()

        _login(client, "mgr")
        declined = client.post(
            f"/api/loans/{loan_id}/actions/decline",
            json={"entries": [{"lineId": client.get(f"/api/loans/{loan_id}").get_json()["lines"][0]["id"], "reason": "kaputt"}]},
        )
        assert declined.status_code == 200
        phase_before = declined.get_json()["phase"]

        failed = client.post(f"/api/loans/{loan_id}/actions/complete-step")
        assert failed.status_code == 409
        assert failed.get_json()["error"] == "mail_not_sent"
        assert len(sent_to) == 2
        assert client.get(f"/api/loans/{loan_id}").get_json()["phase"] == phase_before

        sent_to.clear()
        set_mail_sender_for_tests(
            lambda to, subject, text, html, cc, attachments=None: sent_to.append(to)
        )
        ok = client.post(f"/api/loans/{loan_id}/actions/complete-step")
        assert ok.status_code == 200, ok.get_json()
        assert len(sent_to) == 1
        assert sent_to[0] == "mgr@test.example"
    finally:
        set_mail_sender_for_tests(None)
        tmp.cleanup()


def test_unknown_mail_locale_stays_german():
    assert resolve_locale("en") == "de"
    assert resolve_locale(None) == "de"
    assert t("mail.openLoan", locale="en") == "Verleih öffnen"
