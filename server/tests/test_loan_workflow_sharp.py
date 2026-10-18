from datetime import date, timedelta

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
        upsert_user_from_oidc(session, sub="su", name="SU", email=None, force_superuser=True)
        session.commit()


def _piece(client, inv_id: int, name: str = "Catan") -> int:
    _login(client, "su")
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types",
        json={"name": f"Brettspiel-{name}", "tracking": "piece"},
    )
    type_id = mt.get_json()["id"]
    piece = client.post(
        f"/api/inventories/{inv_id}/pieces",
        json={"materialTypeId": type_id, "name": name},
    )
    return piece.get_json()["id"]


def _flyer_line(client, inv_id: int, loan_id: int, qty: int = 50) -> tuple[int, int]:
    _login(client, "su")
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types",
        json={"name": "Flyer", "tracking": "stock", "consumable": True},
    )
    type_id = mt.get_json()["id"]
    lot = client.post(
        f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
        json={"quantity": 100},
    )
    assert lot.status_code == 201
    _login(client, "borrower")
    res = client.post(
        f"/api/loans/{loan_id}/lines",
        json={"materialTypeId": type_id, "quantity": qty},
    )
    assert res.status_code == 201
    line_id = res.get_json()["lines"][-1]["id"]
    return type_id, line_id


def test_delete_only_in_draft_phase():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        add_piece_line(client, loan_id, piece_id)
        submitted = submit_request(client, loan_id)
        assert submitted.status_code == 200

        _login(client, "borrower")
        res = client.delete(f"/api/loans/{loan_id}")
        assert res.status_code == 409
        assert res.get_json()["error"] == "invalid_loan_state"
    finally:
        tmp.cleanup()


def test_notify_added_batches_lines():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        p1 = _piece(client, inv_id, "A")
        p2 = _piece(client, inv_id, "B")
        _login(client, "borrower")
        add_piece_line(client, loan_id, p1)
        assert submit_request(client, loan_id).status_code == 200

        _login(client, "borrower")
        add_piece_line(client, loan_id, p2)
        detail = client.get(f"/api/loans/{loan_id}").get_json()
        assert detail["hasUnnotifiedRequestedLines"] is True

        from lamathek.services.loan_notifications import set_mail_sender_for_tests

        mails: list[dict] = []

        def capture(*args, **kwargs):
            mails.append({"to": args[0]})

        set_mail_sender_for_tests(capture)
        _login(client, "borrower")
        res = client.post(f"/api/loans/{loan_id}/actions/notify-added")
        assert res.status_code == 200
        assert mails == []
        body = res.get_json()
        assert body["hasUnnotifiedRequestedLines"] is False
        set_mail_sender_for_tests(None)
    finally:
        tmp.cleanup()


def test_restock_consumable_partial():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        _type_id, line_id = _flyer_line(client, inv_id, loan_id, 50)
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        assert confirm_all_lines(client, loan_id, mgr, [line_id]).status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        assert pack_lines(client, loan_id, [line_id]).status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        assert pickup_lines(client, loan_id, [line_id]).status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        _login(client, "mgr")
        reported = client.post(
            f"/api/loans/{loan_id}/actions/report-return",
            json={"lineIds": [line_id]},
        )
        assert reported.status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        restock = client.post(
            f"/api/loans/{loan_id}/actions/restock",
            json={"entries": [{"lineId": line_id, "returnedQuantity": 30}]},
        )
        assert restock.status_code == 200
        line = restock.get_json()["lines"][0]
        assert line["status"] == "restocked"
        assert line["returnedQuantity"] == 30
        stocks = client.get(f"/api/inventories/{inv_id}/stocks").get_json()
        row = next(item for item in stocks if item["materialTypeId"] == _type_id)
        assert row["quantity"] == 80
    finally:
        tmp.cleanup()


def test_restock_from_picked_up_forbidden():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        add_piece_line(client, loan_id, piece_id)
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        line_id = lines[0]["id"]
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        pickup_lines(client, loan_id, [line_id])
        res = client.post(
            f"/api/loans/{loan_id}/actions/restock",
            json={"lineIds": [line_id]},
        )
        assert res.status_code == 409
    finally:
        tmp.cleanup()


def test_meta_frozen_after_request():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        add_piece_line(client, loan_id, piece_id)
        assert submit_request(client, loan_id).status_code == 200
        patched = client.patch(f"/api/loans/{loan_id}", json={"kind": "permanent"})
        assert patched.status_code == 409
    finally:
        tmp.cleanup()


def test_manager_can_cancel_requested_only():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        add_piece_line(client, loan_id, piece_id)
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        res = client.post(f"/api/loans/{loan_id}/actions/cancel")
        assert res.status_code == 200
        assert res.get_json()["phase"] == "closed"
    finally:
        tmp.cleanup()


def test_unpack_and_undo_pickup():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        assert confirm_all_lines(client, loan_id, mgr, [line_id]).status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        assert pack_lines(client, loan_id, [line_id]).status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        unpacked = client.post(
            f"/api/loans/{loan_id}/actions/unpack",
            json={"lineIds": [line_id]},
        )
        assert unpacked.status_code == 200
        assert unpacked.get_json()["lines"][0]["status"] == "confirmed"
        assert pack_lines(client, loan_id, [line_id]).status_code == 200
        assert complete_workflow_step(client, loan_id).status_code == 200
        assert pickup_lines(client, loan_id, [line_id]).status_code == 200
        undone = client.post(
            f"/api/loans/{loan_id}/actions/undo-pickup",
            json={"lineIds": [line_id]},
        )
        assert undone.status_code == 200
        assert undone.get_json()["lines"][0]["status"] == "packed"
    finally:
        tmp.cleanup()


def _rope_line(client, inv_id: int, loan_id: int, qty: int = 10) -> tuple[int, int]:
    _login(client, "su")
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types",
        json={"name": "Seil", "tracking": "stock", "consumable": False},
    )
    type_id = mt.get_json()["id"]
    lot = client.post(
        f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
        json={"quantity": 100},
    )
    assert lot.status_code == 201
    _login(client, "borrower")
    res = client.post(
        f"/api/loans/{loan_id}/lines",
        json={"materialTypeId": type_id, "quantity": qty},
    )
    assert res.status_code == 201
    line_id = res.get_json()["lines"][-1]["id"]
    return type_id, line_id


def test_restock_splits_non_consumable_stock():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        _type_id, line_id = _rope_line(client, inv_id, loan_id, 10)
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        pickup_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        client.post(
            f"/api/loans/{loan_id}/actions/report-return",
            json={"lineIds": [line_id]},
        )
        complete_workflow_step(client, loan_id)
        restock = client.post(
            f"/api/loans/{loan_id}/actions/restock",
            json={
                "entries": [
                    {
                        "lineId": line_id,
                        "returnedQuantity": 6,
                        "reason": "Rest fehlt",
                    }
                ]
            },
        )
        assert restock.status_code == 200
        lines = restock.get_json()["lines"]
        restocked = next(l for l in lines if l["id"] == line_id)
        lost = next(l for l in lines if l["status"] == "not_returned")
        assert restocked["status"] == "restocked"
        assert restocked["quantity"] == 6
        assert lost["quantity"] == 4
        assert lost["reason"] == "Rest fehlt"
        stocks = client.get(f"/api/inventories/{inv_id}/stocks").get_json()
        row = next(item for item in stocks if item["materialTypeId"] == _type_id)
        assert row["quantity"] == 96
    finally:
        tmp.cleanup()


def test_record_loss_requires_reason():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        pickup_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        res = client.post(
            f"/api/loans/{loan_id}/actions/record-loss",
            json={"entries": [{"lineId": line_id}]},
        )
        assert res.status_code == 400
        assert res.get_json()["error"] == "reason_required"
        ok = client.post(
            f"/api/loans/{loan_id}/actions/record-loss",
            json={"entries": [{"lineId": line_id, "reason": "Kaputt"}]},
        )
        assert ok.status_code == 200
        assert ok.get_json()["lines"][0]["status"] == "not_returned"
    finally:
        tmp.cleanup()


def test_confirm_requires_contact_on_loan():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        _login(client, "mgr")
        res = client.post(
            f"/api/loans/{loan_id}/actions/confirm",
            json={"lineIds": [line_id]},
        )
        assert res.status_code == 400
        assert res.get_json()["error"] == "invalid_contact"
    finally:
        tmp.cleanup()


def test_confirm_rejects_draft_line():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        _login(client, "borrower")
        res = confirm_all_lines(client, loan_id, mgr, [line_id])
        assert res.status_code == 403
    finally:
        tmp.cleanup()


def test_pickup_blocked_while_pack_step_open():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        p1 = _piece(client, inv_id, "A")
        p2 = _piece(client, inv_id, "B")
        _login(client, "borrower")
        add_piece_line(client, loan_id, p1)
        add_piece_line(client, loan_id, p2)
        lines = submit_request(client, loan_id).get_json()["lines"]
        by_name = {line["pieceName"]: line["id"] for line in lines}
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [by_name["A"], by_name["B"]])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [by_name["A"]])
        blocked = pickup_lines(client, loan_id, [by_name["A"]])
        assert blocked.status_code == 409
        assert blocked.get_json()["error"] == "workflow_step_mismatch"
    finally:
        tmp.cleanup()


def test_pack_blocked_while_review_mail_pending():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        blocked = pack_lines(client, loan_id, [line_id])
        assert blocked.status_code == 409
        assert blocked.get_json()["error"] == "workflow_step_mismatch"
    finally:
        tmp.cleanup()


def test_decline_restore_then_confirm():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        assert submit_request(client, loan_id).status_code == 200
        _login(client, "mgr")
        declined = client.post(
            f"/api/loans/{loan_id}/actions/decline",
            json={"entries": [{"lineId": line_id, "reason": "Fehler"}]},
        )
        assert declined.status_code == 200
        assert declined.get_json()["lines"][0]["status"] == "unavailable"
        restored = client.post(f"/api/loans/{loan_id}/lines/{line_id}/restore")
        assert restored.status_code == 200
        body = restored.get_json()
        assert body["lines"][0]["status"] == "requested"
        assert body["lines"][0]["reason"] == ""
        assert confirm_all_lines(client, loan_id, mgr, [line_id]).status_code == 200
        assert client.get(f"/api/loans/{loan_id}").get_json()["lines"][0]["status"] == "confirmed"
    finally:
        tmp.cleanup()


def test_revoke_confirm_restore_returns_to_confirmed():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        declined = client.post(
            f"/api/loans/{loan_id}/actions/decline",
            json={"entries": [{"lineId": line_id, "reason": "Versehen"}]},
        )
        assert declined.status_code == 200
        restored = client.post(f"/api/loans/{loan_id}/lines/{line_id}/restore")
        assert restored.status_code == 200
        assert restored.get_json()["lines"][0]["status"] == "confirmed"
    finally:
        tmp.cleanup()


def test_restore_not_packed_reopens_closed_loan():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        piece_id = _piece(client, inv_id)
        _login(client, "borrower")
        line_id = add_piece_line(client, loan_id, piece_id).get_json()["lines"][0]["id"]
        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        not_packed = client.post(
            f"/api/loans/{loan_id}/actions/mark-not-packed",
            json={"entries": [{"lineId": line_id, "reason": "Fehler"}]},
        )
        assert not_packed.status_code == 200
        closed = client.get(f"/api/loans/{loan_id}").get_json()
        assert closed["phase"] == "closed"
        restored = client.post(f"/api/loans/{loan_id}/lines/{line_id}/restore")
        assert restored.status_code == 200
        body = restored.get_json()
        assert body["lines"][0]["status"] == "packed"
        assert body["phase"] == "handover"
    finally:
        tmp.cleanup()


def test_restore_loss_puts_stock_back():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr = manager_id(client)
        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        type_id, line_id = _rope_line(client, inv_id, loan_id, 10)
        submit_request(client, loan_id)
        _login(client, "mgr")
        confirm_all_lines(client, loan_id, mgr, [line_id])
        complete_workflow_step(client, loan_id)
        pack_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        pickup_lines(client, loan_id, [line_id])
        complete_workflow_step(client, loan_id)
        loss = client.post(
            f"/api/loans/{loan_id}/actions/record-loss",
            json={"entries": [{"lineId": line_id, "reason": "Versehen"}]},
        )
        assert loss.status_code == 200
        def stock_qty() -> int:
            rows = client.get(f"/api/inventories/{inv_id}/stocks").get_json()
            row = next(r for r in rows if r["materialTypeId"] == type_id)
            return row["quantity"]

        _login(client, "su")
        qty_before = stock_qty()
        _login(client, "mgr")
        restored = client.post(f"/api/loans/{loan_id}/lines/{line_id}/restore")
        assert restored.status_code == 200
        assert restored.get_json()["lines"][0]["status"] == "picked_up"
        _login(client, "su")
        assert stock_qty() == qty_before + 10
    finally:
        tmp.cleanup()
