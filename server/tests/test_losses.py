"""Verlust als Ereignis (D0009): stock lots are never deleted, corrections are exact."""

from test_availability import World, _day


def _stock_row(w: World, type_id: int) -> dict:
    w.as_("mgr")
    rows = w.client.get(f"/api/inventories/{w.inv}/stocks").get_json()
    return next(r for r in rows if r["materialTypeId"] == type_id)


def _lot_with_label(w: World, type_id: int, label: str, quantity: int) -> int:
    w.as_("mgr")
    created = w.client.post(
        f"/api/inventories/{w.inv}/stocks/{type_id}/lots",
        json={"quantity": quantity, "label": label},
    )
    assert created.status_code in (200, 201), created.get_json()
    return next(l["id"] for l in created.get_json()["lots"] if l["label"] == label)


def _record_loss(w: World, loan_id: int, line_id: int, quantity: int | None = None):
    entry = {"lineId": line_id, "reason": "nicht wiedergekommen"}
    if quantity is not None:
        entry["quantity"] = quantity
    w.as_("mgr")
    return w.client.post(f"/api/loans/{loan_id}/actions/record-loss", json={"entries": [entry]})


def _setup_lost_heringe(w: World, *, lent: int, lost: int | None):
    heringe = w.stock("Hering", 0)
    lot_id = _lot_with_label(w, heringe, "Kiste Hering", 5)
    loan = w.loan([{"materialTypeId": heringe, "quantity": lent}], -3, 3)
    w.hand_out(loan)
    line_id = w.detail(loan)["lines"][0]["id"]
    response = _record_loss(w, loan, line_id, lost)
    assert response.status_code == 200, response.get_json()
    return heringe, lot_id, loan, line_id


def test_partial_loss_splits_the_line_and_can_be_corrected():
    """Reproduced in the review: 2 of 5 lost, then the correction failed."""
    w = World()
    try:
        heringe, _lot, loan, line_id = _setup_lost_heringe(w, lent=5, lost=2)
        lines = {l["id"]: l for l in w.detail(loan)["lines"]}
        assert lines[line_id]["status"] == "picked_up"
        assert lines[line_id]["quantity"] == 3
        lost_line = next(l for l in lines.values() if l["id"] != line_id)
        assert (lost_line["status"], lost_line["quantity"]) == ("not_returned", 2)
        assert _stock_row(w, heringe)["quantity"] == 3

        restored = w.client.post(f"/api/loans/{loan}/lines/{lost_line['id']}/restore")
        assert restored.status_code == 200, restored.get_json()
        assert _stock_row(w, heringe)["quantity"] == 5
    finally:
        w.close()


def test_loss_emptying_a_lot_keeps_lot_label_and_quantity():
    w = World()
    try:
        heringe, lot_id, loan, line_id = _setup_lost_heringe(w, lent=5, lost=None)
        row = _stock_row(w, heringe)
        lot = next(l for l in row["lots"] if l["id"] == lot_id)
        assert (lot["label"], lot["quantity"], lot["lostQuantity"]) == ("Kiste Hering", 5, 5)
        assert row["quantity"] == 0

        assert w.client.post(f"/api/loans/{loan}/lines/{line_id}/restore").status_code == 200
        lot = next(l for l in _stock_row(w, heringe)["lots"] if l["id"] == lot_id)
        assert (lot["label"], lot["quantity"], lot["lostQuantity"]) == ("Kiste Hering", 5, 0)
    finally:
        w.close()


def test_loss_cannot_exceed_the_line():
    w = World()
    try:
        heringe = w.stock("Hering", 10)
        loan = w.loan([{"materialTypeId": heringe, "quantity": 4}], -3, 3)
        w.hand_out(loan)
        line_id = w.detail(loan)["lines"][0]["id"]
        response = _record_loss(w, loan, line_id, 7)
        assert response.status_code == 400
        assert response.get_json()["error"] == "invalid_quantity"
        assert _stock_row(w, heringe)["quantity"] == 10
    finally:
        w.close()


def test_lost_stock_found_again_in_parts_and_written_off():
    w = World()
    try:
        heringe, lot_id, _loan, _line = _setup_lost_heringe(w, lent=5, lost=4)
        losses = w.client.get(f"/api/inventories/{w.inv}/stocks/{heringe}/losses").get_json()
        assert [(l["quantity"], l["open"]) for l in losses] == [(4, True)]
        loss_id = losses[0]["id"]

        no_reason = w.client.post(
            f"/api/inventories/{w.inv}/stock-losses/{loss_id}/found-again", json={"quantity": 1}
        )
        assert no_reason.status_code == 400
        found = w.client.post(
            f"/api/inventories/{w.inv}/stock-losses/{loss_id}/found-again",
            json={"quantity": 1, "reason": "im Anhänger"},
        )
        assert found.status_code == 200, found.get_json()
        assert found.get_json()["resolution"] == "found_again"
        assert _stock_row(w, heringe)["quantity"] == 1 + 1  # 1 still out on the loan

        written = w.client.post(
            f"/api/inventories/{w.inv}/stock-losses/{loss_id}/write-off", json={"reason": "weg"}
        )
        assert written.status_code == 200, written.get_json()
        lot = next(l for l in _stock_row(w, heringe)["lots"] if l["id"] == lot_id)
        assert (lot["quantity"], lot["lostQuantity"]) == (2, 0)
        again = w.client.post(
            f"/api/inventories/{w.inv}/stock-losses/{loss_id}/write-off", json={"reason": "weg"}
        )
        assert again.status_code == 409
    finally:
        w.close()


def test_lot_with_loss_history_cannot_be_deleted():
    w = World()
    try:
        _heringe, lot_id, _loan, _line = _setup_lost_heringe(w, lent=5, lost=1)
        response = w.client.delete(f"/api/inventories/{w.inv}/stock-lots/{lot_id}")
        assert response.status_code == 409
        assert response.get_json()["error"] == "lot_has_history"
    finally:
        w.close()


def test_consumption_lowers_stock_and_correction_brings_it_back():
    w = World()
    try:
        w.as_("mgr")
        flyer = w.client.post(
            f"/api/inventories/{w.inv}/material-types",
            json={"name": "Flyer", "tracking": "stock", "consumable": True},
        ).get_json()["id"]
        w.client.post(f"/api/inventories/{w.inv}/stocks/{flyer}/lots", json={"quantity": 100})
        loan = w.loan([{"materialTypeId": flyer, "quantity": 50}], -3, 3)
        w.hand_out(loan)
        line_id = w.detail(loan)["lines"][0]["id"]
        w.as_("borrower")
        w.client.post(f"/api/loans/{loan}/actions/report-return", json={"lineIds": [line_id]})
        w.step(loan)
        w.as_("mgr")
        restock = w.client.post(
            f"/api/loans/{loan}/actions/restock",
            json={"entries": [{"lineId": line_id, "returnedQuantity": 30}]},
        )
        assert restock.status_code == 200, restock.get_json()
        row = _stock_row(w, flyer)
        assert (row["quantity"], row["lots"][0]["quantity"]) == (80, 80)
        losses = w.client.get(f"/api/inventories/{w.inv}/stocks/{flyer}/losses").get_json()
        assert [(l["kind"], l["quantity"], l["open"]) for l in losses] == [("consumed", 20, False)]
    finally:
        w.close()


def test_total_loss_cannot_be_closed_as_repair_but_can_be_written_off():
    w = World()
    try:
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], -3, 3)
        w.hand_out(loan)
        line_id = w.detail(loan)["lines"][0]["id"]
        assert _record_loss(w, loan, line_id).status_code == 200
        piece = w.client.get(f"/api/pieces/{kohte}").get_json()
        total_loss = next(d for d in piece["damages"] if d["kind"] == "total_loss")

        repaired = w.client.post(
            f"/api/damages/{total_loss['id']}/repairs", json={"recordedOn": _day(0), "note": "x"}
        )
        assert repaired.status_code == 409
        assert repaired.get_json()["error"] == "total_loss_not_repairable"

        written = w.client.post(f"/api/pieces/{kohte}/write-off", json={"reason": "verbrannt"})
        assert written.status_code == 200, written.get_json()
        body = written.get_json()
        assert body["status"] == "retired"
        damage = next(d for d in body["damages"] if d["id"] == total_loss["id"])
        assert damage["repair"]["resolutionKind"] == "written_off"
    finally:
        w.close()


def test_piece_loss_booked_by_mistake_can_be_corrected():
    w = World()
    try:
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], -3, 3)
        w.hand_out(loan)
        line_id = w.detail(loan)["lines"][0]["id"]
        assert _record_loss(w, loan, line_id).status_code == 200
        restored = w.client.post(f"/api/loans/{loan}/lines/{line_id}/restore")
        assert restored.status_code == 200, restored.get_json()
        assert restored.get_json()["lines"][0]["status"] == "picked_up"
        piece = w.client.get(f"/api/pieces/{kohte}").get_json()
        damage = next(d for d in piece["damages"] if d["kind"] == "total_loss")
        assert damage["repair"]["resolutionKind"] == "cancelled_mistake"
    finally:
        w.close()
