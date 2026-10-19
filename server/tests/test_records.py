"""Journal completeness, PDF lists, iCal format and dashboard cards (Paket 6)."""

from datetime import date, datetime, timezone

from lamathek.db import get_session
from lamathek.services.calendar import ics_fold, ics_for_loans
from lamathek.services.loan_pdf import pdf_rows_for_loan
from lamathek.services.loans import loan_by_id
from test_availability import World, _day


def _journal(w: World, loan_id: int, *, as_: str = "mgr") -> list[dict]:
    w.as_(as_)
    response = w.client.get(f"/api/loans/{loan_id}/journal")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_journal_records_creation_lines_requests_and_changes():
    w = World()
    try:
        kohte = w.piece("K1")
        heringe = w.stock("Hering", 20)
        loan = w.loan(
            [{"pieceId": kohte}, {"materialTypeId": heringe, "quantity": 6}], 5, 7
        )
        w.as_("borrower")
        w.client.post(
            f"/api/loans/{loan}/lines",
            json={"materialTypeId": heringe, "quantity": 4, "reason": "weniger Zelte"},
        )
        w.as_("mgr")
        w.client.patch(f"/api/loans/{loan}", json={"pickupOn": _day(4)})

        entries = _journal(w, loan)
        kinds = [e["kind"] for e in entries]
        for kind in ("loan.created", "line.added", "line.request", "line.quantity_changed", "loan.updated"):
            assert kind in kinds, kind
        added = [e["payload"]["item"] for e in entries if e["kind"] == "line.added"]
        assert sorted(added) == ["6 × Hering", "K1"]
        change = next(e for e in entries if e["kind"] == "line.quantity_changed")["payload"]
        assert (change["fromQuantity"], change["toQuantity"], change["reason"]) == (6, 4, "weniger Zelte")
        updated = next(e for e in entries if e["kind"] == "loan.updated")["payload"]
        assert updated["changes"]["pickupOn"] == {"from": _day(5), "to": _day(4)}
        w.client.patch(f"/api/loans/{loan}", json={"contactUserId": w.mgr})
        contact = next(e for e in _journal(w, loan) if "contact" in e["payload"].get("changes", {}))
        assert contact["payload"]["changes"]["contact"] == {"from": None, "to": "mgr"}
        assert all(e["createdAt"].endswith("+00:00") for e in entries)
    finally:
        w.close()


def test_journal_records_removed_draft_line_and_cancellation():
    w = World()
    try:
        k1, k2 = w.piece("K1"), w.piece("K2")
        w.as_("borrower")
        draft = w.client.post(
            f"/api/inventories/{w.inv}/loans", json={"groupName": "Stamm", "borrowerUserId": w.bor}
        ).get_json()
        line = w.client.post(f"/api/loans/{draft['id']}/lines", json={"pieceId": k1}).get_json()["lines"][0]
        w.client.delete(f"/api/loans/{draft['id']}/lines/{line['id']}")
        # Drafts are visible to their borrower only.
        assert "line.removed" in [e["kind"] for e in _journal(w, draft["id"], as_="borrower")]

        loan = w.loan([{"pieceId": k2}], 5, 7)
        w.as_("borrower")
        assert w.client.post(f"/api/loans/{loan}/actions/cancel").status_code == 200
        cancel = [e for e in _journal(w, loan) if e["kind"] == "line.cancel"]
        assert [e["payload"]["item"] for e in cancel] == ["K2"]
    finally:
        w.close()


def test_pdf_lists_show_status_and_keep_ended_lines_apart():
    w = World()
    try:
        k1, k2 = w.piece("K1"), w.piece("K2")
        loan = w.loan([{"pieceId": k1}, {"pieceId": k2}], 5, 7)
        lines = {l["pieceId"]: l["id"] for l in w.detail(loan)["lines"]}
        w.as_("mgr")
        w.client.patch(f"/api/loans/{loan}", json={"contactUserId": w.mgr})
        w.client.post(
            f"/api/loans/{loan}/actions/decline",
            json={"entries": [{"lineId": lines[k2], "reason": "kaputt"}]},
        )
        assert w.confirm(loan, [lines[k1]]).status_code == 200
        assert w.step(loan).status_code == 200
        with w.app.app_context():
            active, ended = pdf_rows_for_loan(loan_by_id(get_session(), loan))
        assert [(r["itemLabel"], r["statusLabel"]) for r in active] == [("K1", "Bestätigt")]
        assert [(r["itemLabel"], r["statusLabel"]) for r in ended] == [("K2", "Nicht verfügbar")]

        for kind in ("pack",):
            response = w.client.get(f"/api/loans/{loan}/pdf/{kind}")
            assert response.status_code == 200 and response.data[:4] == b"%PDF"
        w.client.post(f"/api/loans/{loan}/actions/pack", json={"lineIds": [lines[k1]]})
        w.step(loan)
        assert w.client.get(f"/api/loans/{loan}/pdf/handover").status_code == 200
        w.client.post(f"/api/loans/{loan}/actions/pickup", json={"lineIds": [lines[k1]]})
        w.step(loan)
        assert w.client.get(f"/api/loans/{loan}/pdf/return").status_code == 200
    finally:
        w.close()


def test_ics_permanent_is_one_day_without_prefix_and_lines_are_folded():
    w = World()
    try:
        kohte = w.piece()
        permanent = w.loan([{"pieceId": kohte}], 5, None, kind="permanent")
        with w.app.app_context():
            loan = loan_by_id(get_session(), permanent)
            stamp = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
            body = ics_for_loans([loan], now=stamp)
        start = date.fromisoformat(_day(5))
        assert f"DTSTART;VALUE=DATE:{start:%Y%m%d}" in body
        assert f"DTEND;VALUE=DATE:{date.fromordinal(start.toordinal() + 1):%Y%m%d}" in body
        assert "DTSTAMP:20261020T080000Z" in body
        assert "Dauerleihgabe:" not in body
        assert all(len(line.encode()) <= 75 for line in body.split("\r\n"))
    finally:
        w.close()


def test_ics_fold_keeps_multibyte_characters_whole():
    folded = ics_fold("SUMMARY:" + "Ä" * 60)
    assert all(len(part.encode()) <= 75 for part in folded)
    assert "".join(p[1:] if i else p for i, p in enumerate(folded)) == "SUMMARY:" + "Ä" * 60


def test_dashboard_cards_for_materialwarte():
    w = World()
    try:
        kohte = w.piece()
        first = w.loan([{"pieceId": kohte}], 10, 14)
        clash = w.loan([{"pieceId": kohte}], 12, 16)
        assert w.confirm(first).status_code == 200
        w.as_("mgr")
        cards = w.client.get("/api/dashboard").get_json()["cards"]
        assert [c["id"] for c in cards["conflicts"]] == [clash]
        assert {c["id"] for c in cards["openRequests"]} == {first, clash}
        assert cards["myLoans"] == []
        w.as_("borrower")
        mine = w.client.get("/api/dashboard").get_json()
        assert {c["id"] for c in mine["cards"]["myLoans"]} == {first, clash}
        assert mine["cards"]["conflicts"] == [] and mine["canManage"] is False
    finally:
        w.close()
