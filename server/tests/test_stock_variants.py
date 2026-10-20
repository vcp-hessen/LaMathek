"""Mengen mit Varianten (#12): a Mengenposten is one Materialart + one full combination."""

from test_availability import World


def _seil(w: World) -> int:
    """Seil with Länge 3 m (20) and 4 m (6), as two Mengenposten."""
    w.as_("mgr")
    mt = w.client.post(
        f"/api/inventories/{w.inv}/material-types",
        json={"name": "Seil", "tracking": "stock", "variants": [{"label": "Länge", "values": ["3 m", "4 m"]}]},
    )
    assert mt.status_code == 201, mt.get_json()
    type_id = mt.get_json()["id"]
    for length, quantity in (("3 m", 20), ("4 m", 6)):
        lot = w.client.post(
            f"/api/inventories/{w.inv}/stocks/{type_id}/lots",
            json={"quantity": quantity, "variant": {"Länge": length}},
        )
        assert lot.status_code in (200, 201), lot.get_json()
    return type_id


def _available(w: World, type_id: int) -> dict[str, int]:
    w.as_("mgr")
    row = next(r for r in w.client.get(f"/api/inventories/{w.inv}/stocks").get_json() if r["materialTypeId"] == type_id)
    result: dict[str, int] = {}
    for lot in row["lots"]:
        key = lot["variant"].get("Länge", "")
        result[key] = result.get(key, 0) + lot["quantity"] - lot.get("lostQuantity", 0)
    return result


def test_a_lot_needs_the_full_combination():
    w = World()
    try:
        type_id = _seil(w)
        mixed = w.client.post(
            f"/api/inventories/{w.inv}/stocks/{type_id}/lots", json={"quantity": 5}
        )
        assert mixed.status_code == 400
        assert mixed.get_json()["error"] == "variant_required"
    finally:
        w.close()


def test_set_lists_two_lengths_and_the_loan_keeps_them_apart():
    w = World()
    try:
        type_id = _seil(w)
        jurte = w.client.post(f"/api/inventories/{w.inv}/sets", json={"name": "Jurte"}).get_json()
        for length, quantity in (("3 m", 12), ("4 m", 3)):
            saved = w.client.put(
                f"/api/sets/{jurte['id']}/stock-lines",
                json={"materialTypeId": type_id, "role": "assignment", "quantity": quantity, "variant": {"Länge": length}},
            )
            assert saved.status_code == 200, saved.get_json()
        detail = w.client.get(f"/api/sets/{jurte['id']}").get_json()
        assert sorted((l["stockVariant"]["Länge"], l["quantity"]) for l in detail["assignmentStock"]) == [
            ("3 m", 12),
            ("4 m", 3),
        ]
        too_many = w.client.put(
            f"/api/sets/{jurte['id']}/stock-lines",
            json={"materialTypeId": type_id, "role": "optional", "quantity": 7, "variant": {"Länge": "4 m"}},
        )
        assert too_many.status_code == 409

        loan = w.loan([{"setId": jurte["id"]}], 5, 7)
        lines = w.detail(loan)["lines"]
        assert sorted((l["stockVariant"]["Länge"], l["quantity"]) for l in lines) == [("3 m", 12), ("4 m", 3)]
    finally:
        w.close()


def test_only_the_short_length_is_overbooked():
    w = World()
    try:
        type_id = _seil(w)

        def rope(length: str, quantity: int) -> dict:
            return {"materialTypeId": type_id, "quantity": quantity, "variant": {"Länge": length}}

        first = w.loan([rope("3 m", 12), rope("4 m", 3)], 5, 7)
        second = w.loan([rope("3 m", 8), rope("4 m", 3)], 6, 8)
        third = w.loan([rope("4 m", 1)], 6, 6)
        assert w.confirm(first).status_code == 200
        assert w.confirm(second).status_code == 200  # 20 of 20 × 3 m, 6 of 6 × 4 m
        refused = w.confirm(third)
        assert refused.status_code == 409
        conflict = refused.get_json()["conflicts"][0]
        assert (conflict["code"], conflict["available"], conflict["occupied"]) == ("stock_short", 6, 6)
        labels = {w_["itemLabel"] for w_ in w.detail(third)["warnings"]}
        assert labels == {"1 × Seil (4 m)"}
    finally:
        w.close()


def test_a_loss_only_touches_its_length():
    w = World()
    try:
        type_id = _seil(w)
        loan = w.loan([{"materialTypeId": type_id, "quantity": 2, "variant": {"Länge": "4 m"}}], -3, 3)
        w.hand_out(loan)
        line_id = w.detail(loan)["lines"][0]["id"]
        w.as_("mgr")
        lost = w.client.post(
            f"/api/loans/{loan}/actions/record-loss",
            json={"entries": [{"lineId": line_id, "reason": "gerissen"}]},
        )
        assert lost.status_code == 200, lost.get_json()
        assert _available(w, type_id) == {"3 m": 20, "4 m": 4}
        journal = w.client.get(f"/api/loans/{loan}/journal").get_json()
        assert any(e["payload"].get("item") == "2 × Seil (4 m)" for e in journal)
    finally:
        w.close()


def test_stock_line_without_combination_is_refused():
    w = World()
    try:
        type_id = _seil(w)
        w.as_("borrower")
        draft = w.client.post(
            f"/api/inventories/{w.inv}/loans", json={"groupName": "Stamm", "borrowerUserId": w.bor}
        ).get_json()
        response = w.client.post(
            f"/api/loans/{draft['id']}/lines", json={"materialTypeId": type_id, "quantity": 2}
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "variant_required"
    finally:
        w.close()
