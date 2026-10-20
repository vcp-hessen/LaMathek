"""Datumsbasierte Verfügbarkeit (D0007): periods, stock peaks, gates and warnings."""

from datetime import timedelta

from conftest import app_with_db, login
from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc
from lamathek.timezone import instance_today
from loan_helpers import borrower_id, manager_id, setup_inventory

TODAY = instance_today()


def _day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


class World:
    """One Inventar with a Materialwart, a borrower and helpers to drive Verleihe."""

    def __init__(self):
        self.app, self.tmp = app_with_db()
        with self.app.app_context():
            session = get_session()
            upsert_user_from_oidc(session, sub="su", name="su", email="su@x", force_superuser=True)
            session.commit()
        self.client = self.app.test_client()
        self.inv = setup_inventory(self.client, visibility="active")
        self.mgr = manager_id(self.client)
        self.bor = borrower_id(self.client)

    def close(self):
        self.tmp.cleanup()

    def as_(self, sub: str) -> "World":
        login(self.client, sub)
        return self

    def piece(self, name: str = "Kohte 1") -> int:
        self.as_("mgr")
        mt = self.client.post(
            f"/api/inventories/{self.inv}/material-types",
            json={"name": f"Art {name}", "tracking": "piece"},
        ).get_json()
        return self.client.post(
            f"/api/inventories/{self.inv}/pieces",
            json={"materialTypeId": mt["id"], "name": name},
        ).get_json()["id"]

    def stock(self, name: str, quantity: int) -> int:
        self.as_("mgr")
        mt = self.client.post(
            f"/api/inventories/{self.inv}/material-types",
            json={"name": name, "tracking": "stock"},
        ).get_json()
        self.client.post(
            f"/api/inventories/{self.inv}/stocks/{mt['id']}/lots", json={"quantity": quantity}
        )
        return mt["id"]

    def loan(self, lines: list[dict], start: int, end: int | None, *, kind: str = "short") -> int:
        self.as_("borrower")
        loan = self.client.post(
            f"/api/inventories/{self.inv}/loans",
            json={"groupName": "Stamm", "borrowerUserId": self.bor, "kind": kind},
        ).get_json()
        for line in lines:
            assert self.client.post(f"/api/loans/{loan['id']}/lines", json=line).status_code == 201
        body = {"pickupOn": _day(start)}
        if end is not None:
            body["returnOn"] = _day(end)
        response = self.client.post(f"/api/loans/{loan['id']}/actions/request", json=body)
        assert response.status_code == 200, response.get_json()
        return loan["id"]

    def detail(self, loan_id: int) -> dict:
        self.as_("mgr")
        return self.client.get(f"/api/loans/{loan_id}").get_json()

    def confirm(self, loan_id: int, line_ids: list[int] | None = None):
        self.as_("mgr")
        self.client.patch(f"/api/loans/{loan_id}", json={"contactUserId": self.mgr})
        if line_ids is None:
            line_ids = [l["id"] for l in self.detail(loan_id)["lines"] if l["status"] == "requested"]
        return self.client.post(f"/api/loans/{loan_id}/actions/confirm", json={"lineIds": line_ids})

    def step(self, loan_id: int):
        return self.client.post(f"/api/loans/{loan_id}/actions/complete-step")

    def hand_out(self, loan_id: int):
        """Confirm, pack and pick up every line."""
        assert self.confirm(loan_id).status_code == 200
        assert self.step(loan_id).status_code == 200
        ids = [l["id"] for l in self.detail(loan_id)["lines"]]
        assert self.client.post(f"/api/loans/{loan_id}/actions/pack", json={"lineIds": ids}).status_code == 200
        assert self.step(loan_id).status_code == 200
        assert self.client.post(f"/api/loans/{loan_id}/actions/pickup", json={"lineIds": ids}).status_code == 200
        assert self.step(loan_id).status_code == 200


def _codes(detail: dict) -> list[str]:
    return [w["code"] for w in detail.get("warnings", [])]


def test_piece_can_be_booked_for_two_separate_periods():
    w = World()
    try:
        kohte = w.piece()
        july = w.loan([{"pieceId": kohte}], 10, 14)
        august = w.loan([{"pieceId": kohte}], 30, 35)
        assert w.confirm(july).status_code == 200
        assert w.confirm(august).status_code == 200
    finally:
        w.close()


def test_overlapping_piece_is_refused_with_the_conflicting_loan():
    w = World()
    try:
        kohte = w.piece()
        first = w.loan([{"pieceId": kohte}], 10, 14)
        second = w.loan([{"pieceId": kohte}], 12, 20)
        assert w.confirm(first).status_code == 200
        assert "piece_booked" in _codes(w.detail(second))

        refused = w.confirm(second)
        assert refused.status_code == 409
        body = refused.get_json()
        assert body["error"] == "piece_unavailable"
        assert body["conflicts"][0]["code"] == "piece_booked"
        assert body["conflicts"][0]["otherLoanId"] == first
    finally:
        w.close()


def test_return_day_and_pickup_day_on_the_same_date_conflict():
    w = World()
    try:
        kohte = w.piece()
        first = w.loan([{"pieceId": kohte}], 10, 14)
        second = w.loan([{"pieceId": kohte}], 14, 16)
        assert w.confirm(first).status_code == 200
        assert w.confirm(second).status_code == 409
    finally:
        w.close()


def test_permanent_loan_blocks_without_end():
    w = World()
    try:
        kohte = w.piece()
        permanent = w.loan([{"pieceId": kohte}], 5, None, kind="permanent")
        much_later = w.loan([{"pieceId": kohte}], 400, 410)
        assert w.confirm(permanent).status_code == 200
        assert w.confirm(much_later).status_code == 409
    finally:
        w.close()


def test_overdue_piece_blocks_today_but_not_next_month():
    w = World()
    try:
        kohte = w.piece()
        overdue = w.loan([{"pieceId": kohte}], -10, -3)
        w.hand_out(overdue)
        now = w.loan([{"pieceId": kohte}], 0, 2)
        later = w.loan([{"pieceId": kohte}], 30, 32)
        refused = w.confirm(now)
        assert refused.status_code == 409
        assert refused.get_json()["conflicts"][0]["code"] == "piece_overdue"
        assert w.confirm(later).status_code == 200
    finally:
        w.close()


def test_stock_peak_counts_concurrent_loans_not_pairs():
    w = World()
    try:
        heringe = w.stock("Hering", 10)
        a = w.loan([{"materialTypeId": heringe, "quantity": 4}], 10, 20)
        b = w.loan([{"materialTypeId": heringe, "quantity": 4}], 15, 25)
        c = w.loan([{"materialTypeId": heringe, "quantity": 4}], 18, 19)
        d = w.loan([{"materialTypeId": heringe, "quantity": 6}], 21, 22)
        assert w.confirm(a).status_code == 200
        assert w.confirm(b).status_code == 200
        refused = w.confirm(c)  # day 18: 4 + 4 + 4 > 10
        assert refused.status_code == 409
        conflict = refused.get_json()["conflicts"][0]
        assert conflict == {
            "code": "stock_short",
            "lineId": conflict["lineId"],
            "pieceId": None,
            "materialTypeId": heringe,
            "otherLoanId": None,
            "otherLoanTitle": None,
            "otherInventoryId": None,
            "itemLabel": "4 × Hering",
            "available": 10,
            "occupied": 8,
            "requested": 4,
        }
        assert w.confirm(d).status_code == 200  # day 21: only b (4) + 6 = 10
    finally:
        w.close()


def test_two_lines_of_the_same_type_on_one_loan_cannot_exceed_stock():
    """Reproduced in the review: 16 Heringe confirmed with 10 in stock."""
    w = World()
    try:
        heringe = w.stock("Hering", 10)
        jurte = w.client.post(f"/api/inventories/{w.inv}/sets", json={"name": "Jurte"}).get_json()
        w.client.put(
            f"/api/sets/{jurte['id']}/stock-lines",
            json={"materialTypeId": heringe, "role": "assignment", "quantity": 8},
        )
        loan = w.loan([{"setId": jurte["id"]}, {"materialTypeId": heringe, "quantity": 8}], 5, 7)
        assert w.confirm(loan).status_code == 409
        lines = w.detail(loan)["lines"]
        assert [l["status"] for l in lines] == ["requested", "requested"]
    finally:
        w.close()


def test_restore_to_occupying_status_checks_the_period_again():
    w = World()
    try:
        kohte = w.piece()
        first = w.loan([{"pieceId": kohte}], 3, 6)
        assert w.confirm(first).status_code == 200
        assert w.step(first).status_code == 200
        line_id = w.detail(first)["lines"][0]["id"]
        w.client.post(f"/api/loans/{first}/actions/pack", json={"lineIds": [line_id]})
        w.step(first)
        not_picked = w.client.post(
            f"/api/loans/{first}/actions/mark-not-picked-up",
            json={"entries": [{"lineId": line_id, "reason": "nicht erschienen"}]},
        )
        assert not_picked.status_code == 200, not_picked.get_json()

        second = w.loan([{"pieceId": kohte}], 4, 8)
        assert w.confirm(second).status_code == 200

        restored = w.client.post(f"/api/loans/{first}/lines/{line_id}/restore")
        assert restored.status_code == 409
        assert restored.get_json()["conflicts"][0]["otherLoanId"] == second
    finally:
        w.close()


def test_moving_confirmed_dates_onto_a_booking_is_refused():
    w = World()
    try:
        kohte = w.piece()
        first = w.loan([{"pieceId": kohte}], 10, 12)
        second = w.loan([{"pieceId": kohte}], 20, 22)
        assert w.confirm(first).status_code == 200
        assert w.confirm(second).status_code == 200
        moved = w.client.patch(f"/api/loans/{second}", json={"pickupOn": _day(11)})
        assert moved.status_code == 409
        assert moved.get_json()["error"] == "dates_conflict"
        assert w.detail(second)["pickupOn"] == _day(20)
        assert w.client.patch(f"/api/loans/{second}", json={"pickupOn": _day(15)}).status_code == 200
    finally:
        w.close()


def test_lifting_permanent_needs_a_return_date():
    w = World()
    try:
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], 5, None, kind="permanent")
        assert w.confirm(loan).status_code == 200
        response = w.client.patch(f"/api/loans/{loan}", json={"kind": "short"})
        assert response.status_code == 400
        assert response.get_json()["error"] == "return_required"
        both = w.client.patch(f"/api/loans/{loan}", json={"kind": "short", "returnOn": _day(9)})
        assert both.status_code == 200, both.get_json()
    finally:
        w.close()


def test_lowering_stock_by_hand_respects_future_bookings_only():
    w = World()
    try:
        heringe = w.stock("Hering", 10)
        loan = w.loan([{"materialTypeId": heringe, "quantity": 8}], 5, 7)
        assert w.confirm(loan).status_code == 200
        lots = w.client.get(f"/api/inventories/{w.inv}/stocks").get_json()
        lot = next(s for s in lots if s["materialTypeId"] == heringe)["lots"][0]
        too_low = w.client.patch(
            f"/api/inventories/{w.inv}/stock-lots/{lot['id']}", json={"quantity": 7}
        )
        assert too_low.status_code == 409
        assert too_low.get_json()["error"] == "below_loaned"
        assert w.client.patch(
            f"/api/inventories/{w.inv}/stock-lots/{lot['id']}", json={"quantity": 8}
        ).status_code == 200
    finally:
        w.close()


def test_draft_line_can_be_removed():
    w = World()
    try:
        kohte = w.piece()
        w.as_("borrower")
        loan = w.client.post(
            f"/api/inventories/{w.inv}/loans", json={"groupName": "Stamm", "borrowerUserId": w.bor}
        ).get_json()
        line = w.client.post(f"/api/loans/{loan['id']}/lines", json={"pieceId": kohte}).get_json()["lines"][0]
        removed = w.client.delete(f"/api/loans/{loan['id']}/lines/{line['id']}")
        assert removed.status_code == 204
        assert w.client.get(f"/api/loans/{loan['id']}").get_json()["lines"] == []
    finally:
        w.close()


def test_replacement_must_come_from_the_same_inventory():
    w = World()
    try:
        kohte = w.piece("K1")
        w.as_("su")
        other_inv = w.client.post("/api/inventories", json={"name": "Anderswo"}).get_json()["id"]
        mt = w.client.post(
            f"/api/inventories/{other_inv}/material-types", json={"name": "Fremd", "tracking": "piece"}
        ).get_json()
        foreign = w.client.post(
            f"/api/inventories/{other_inv}/pieces", json={"materialTypeId": mt["id"], "name": "F"}
        ).get_json()["id"]
        loan = w.loan([{"pieceId": kohte}], 5, 7)
        line_id = w.detail(loan)["lines"][0]["id"]
        w.as_("mgr")
        w.client.patch(f"/api/loans/{loan}", json={"contactUserId": w.mgr})
        response = w.client.post(
            f"/api/loans/{loan}/actions/replace",
            json={"originalLineId": line_id, "reason": "kaputt", "replacement": {"pieceId": foreign}},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "invalid_piece"
        assert w.detail(loan)["lines"][0]["status"] == "requested"
    finally:
        w.close()


def test_set_skips_pieces_that_cannot_go_out():
    w = World()
    try:
        good = w.piece("DV 1")
        broken = w.piece("DV 2")
        jurte = w.client.post(f"/api/inventories/{w.inv}/sets", json={"name": "Jurte"}).get_json()
        for piece in (good, broken):
            member = w.client.put(
                f"/api/sets/{jurte['id']}/pieces", json={"pieceId": piece, "role": "assignment"}
            )
            assert member.status_code == 200, member.get_json()
        damage = w.client.post(
            f"/api/pieces/{broken}/damages",
            json={"note": "Riss", "severe": True, "recordedOn": _day(0)},
        )
        assert damage.status_code == 201, damage.get_json()
        w.as_("borrower")
        loan = w.client.post(
            f"/api/inventories/{w.inv}/loans", json={"groupName": "Stamm", "borrowerUserId": w.bor}
        ).get_json()
        added = w.client.post(f"/api/loans/{loan['id']}/lines", json={"setId": jurte["id"]})
        assert added.status_code == 201
        body = added.get_json()
        assert [l["pieceId"] for l in body["lines"]] == [good]
        assert body["skippedPieces"] == [
            {"pieceId": broken, "pieceName": "DV 2", "code": "piece_severe_damage"}
        ]
    finally:
        w.close()


def test_piece_with_loan_history_cannot_be_deleted():
    w = World()
    try:
        kohte = w.piece()
        w.loan([{"pieceId": kohte}], 5, 7)
        w.as_("mgr")
        response = w.client.delete(f"/api/pieces/{kohte}")
        assert response.status_code == 409
        assert response.get_json()["error"] == "piece_has_history"
    finally:
        w.close()


def test_shrinking_a_requested_quantity_needs_a_reason():
    w = World()
    try:
        heringe = w.stock("Hering", 10)
        loan = w.loan([{"materialTypeId": heringe, "quantity": 6}], 5, 7)
        w.as_("borrower")
        refused = w.client.post(
            f"/api/loans/{loan}/lines", json={"materialTypeId": heringe, "quantity": 4}
        )
        assert refused.status_code == 400
        assert refused.get_json()["error"] == "reason_required"
        ok = w.client.post(
            f"/api/loans/{loan}/lines",
            json={"materialTypeId": heringe, "quantity": 4, "reason": "weniger Zelte"},
        )
        assert ok.status_code == 201
    finally:
        w.close()


def test_superuser_cannot_delete_a_loan_after_handover():
    w = World()
    try:
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], 0, 3)
        w.hand_out(loan)
        w.as_("su")
        response = w.client.delete(f"/api/loans/{loan}")
        assert response.status_code == 409
    finally:
        w.close()


def test_confirm_names_every_conflicting_line_and_confirms_none():
    w = World()
    try:
        kohte = w.piece("Kohte 1")
        heringe = w.stock("Hering", 10)
        first = w.loan([{"pieceId": kohte}, {"materialTypeId": heringe, "quantity": 8}], 5, 7)
        assert w.confirm(first).status_code == 200
        second = w.loan([{"pieceId": kohte}, {"materialTypeId": heringe, "quantity": 4}], 6, 8)
        refused = w.confirm(second)
        assert refused.status_code == 409
        body = refused.get_json()
        assert body["error"] == "piece_unavailable"
        assert sorted(c["itemLabel"] for c in body["conflicts"]) == ["4 × Hering", "Kohte 1"]
        # All or nothing: no line of the second Verleih was confirmed.
        assert {l["status"] for l in w.detail(second)["lines"]} == {"requested"}
    finally:
        w.close()
