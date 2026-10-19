from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def _setup_inventory(client):
    _login(client, "su")
    inv = client.post("/api/inventories", json={"name": "Donnerskopf"})
    assert inv.status_code == 201
    return inv.get_json()["id"]


def test_piece_cannot_sit_on_two_sets():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            session.commit()

        client = app.test_client()
        inv_id = _setup_inventory(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        piece_id = piece.get_json()["id"]

        set_a = client.post(f"/api/inventories/{inv_id}/sets", json={"name": "Set A"})
        set_b = client.post(f"/api/inventories/{inv_id}/sets", json={"name": "Set B"})
        set_a_id = set_a.get_json()["id"]
        set_b_id = set_b.get_json()["id"]

        ok = client.put(
            f"/api/sets/{set_a_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )
        assert ok.status_code == 200

        conflict = client.put(
            f"/api/sets/{set_b_id}/pieces",
            json={"pieceId": piece_id, "role": "optional"},
        )
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_on_other_set"
    finally:
        tmp.cleanup()


def test_set_stock_line_cannot_exceed_total_but_sets_reserve_nothing():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            session.commit()

        client = app.test_client()
        inv_id = _setup_inventory(client)

        heringe = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        type_id = heringe.get_json()["id"]
        client.post(
            f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
            json={"quantity": 10},
        )

        set_a = client.post(f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"})
        set_id = set_a.get_json()["id"]

        ok = client.put(
            f"/api/sets/{set_id}/stock-lines",
            json={"materialTypeId": type_id, "role": "optional", "quantity": 8},
        )
        assert ok.status_code == 200

        # Sets reserve nothing (D0007): 8 optional + 5 assigned of 10 is fine,
        # the loan check counts the quantities when they are confirmed.
        second_set = client.post(f"/api/inventories/{inv_id}/sets", json={"name": "Kohte"})
        both = client.put(
            f"/api/sets/{second_set.get_json()['id']}/stock-lines",
            json={"materialTypeId": type_id, "role": "assignment", "quantity": 5},
        )
        assert both.status_code == 200

        over = client.put(
            f"/api/sets/{set_id}/stock-lines",
            json={"materialTypeId": type_id, "role": "assignment", "quantity": 11},
        )
        assert over.status_code == 409
        assert over.get_json()["error"] == "over_reserved"
    finally:
        tmp.cleanup()


def test_stock_line_rejects_other_inventory_material_type():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            session.commit()

        client = app.test_client()
        _login(client, "su")
        inv_a = client.post("/api/inventories", json={"name": "A"})
        inv_b = client.post("/api/inventories", json={"name": "B"})
        inv_a_id = inv_a.get_json()["id"]
        inv_b_id = inv_b.get_json()["id"]

        heringe = client.post(
            f"/api/inventories/{inv_a_id}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        type_id = heringe.get_json()["id"]

        set_b = client.post(f"/api/inventories/{inv_b_id}/sets", json={"name": "X"})
        set_b_id = set_b.get_json()["id"]

        denied = client.put(
            f"/api/sets/{set_b_id}/stock-lines",
            json={"materialTypeId": type_id, "role": "optional", "quantity": 1},
        )
        assert denied.status_code == 404
    finally:
        tmp.cleanup()


def test_materialwart_without_berechtigung_forbidden():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            upsert_user_from_oidc(
                session, sub="mw", name="MW", email=None, force_superuser=False
            )
            session.commit()

        client = app.test_client()
        inv_id = _setup_inventory(client)

        _login(client, "mw")
        assert client.get(f"/api/inventories/{inv_id}/sets").status_code == 403
    finally:
        tmp.cleanup()
