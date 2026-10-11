from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def _setup_inventories(client):
    _login(client, "su")
    a = client.post("/api/inventories", json={"name": "A"})
    b = client.post("/api/inventories", json={"name": "B"})
    assert a.status_code == 201 and b.status_code == 201
    return a.get_json()["id"], b.get_json()["id"]


def test_material_types_scoped_to_inventory():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        inv_a, inv_b = _setup_inventories(client)

        created = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={"name": "Brettspiel", "tracking": "piece", "variants": []},
        )
        assert created.status_code == 201
        type_id = created.get_json()["id"]

        listed_a = client.get(f"/api/inventories/{inv_a}/material-types")
        listed_b = client.get(f"/api/inventories/{inv_b}/material-types")
        assert len(listed_a.get_json()) == 1
        assert listed_b.get_json() == []

        denied = client.post(
            f"/api/inventories/{inv_b}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
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
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            upsert_user_from_oidc(
                session,
                sub="mw",
                name="MW",
                email=None,
                force_superuser=False,
            )
            session.commit()

        client = app.test_client()
        inv_a, _ = _setup_inventories(client)

        _login(client, "mw")
        assert client.get(f"/api/inventories/{inv_a}/material-types").status_code == 403
    finally:
        tmp.cleanup()


def test_stock_type_cannot_receive_piece():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        inv_a, _ = _setup_inventories(client)

        heringe = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        assert heringe.status_code == 201
        type_id = heringe.get_json()["id"]

        piece = client.post(
            f"/api/inventories/{inv_a}/pieces",
            json={"materialTypeId": type_id, "name": "X"},
        )
        assert piece.status_code == 400
        assert piece.get_json()["error"] == "not_piece_tracking"
    finally:
        tmp.cleanup()


def test_variant_must_be_allowed_value():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        inv_a, _ = _setup_inventories(client)

        plane = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Kohtenplane",
                "tracking": "piece",
                "variants": [
                    {"label": "Randstreifen", "values": ["0 cm", "35 cm"]},
                ],
            },
        )
        assert plane.status_code == 201
        type_id = plane.get_json()["id"]

        bad = client.post(
            f"/api/inventories/{inv_a}/pieces",
            json={
                "materialTypeId": type_id,
                "name": "P1",
                "variant": {"Randstreifen": "99 cm"},
            },
        )
        assert bad.status_code == 400
        assert bad.get_json()["error"] == "invalid_variant"

        good = client.post(
            f"/api/inventories/{inv_a}/pieces",
            json={
                "materialTypeId": type_id,
                "name": "P1",
                "variant": {"Randstreifen": "35 cm"},
            },
        )
        assert good.status_code == 201
    finally:
        tmp.cleanup()


def test_material_type_can_gain_variant_axis_while_pieces_exist():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        inv_a, _ = _setup_inventories(client)

        created = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Kohtenplane",
                "tracking": "piece",
                "variants": [{"label": "Randstreifen", "values": ["35 cm"]}],
            },
        )
        type_id = created.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_a}/pieces",
            json={
                "materialTypeId": type_id,
                "name": "P1",
                "variant": {"Randstreifen": "35 cm"},
            },
        )
        assert piece.status_code == 201

        updated = client.patch(
            f"/api/material-types/{type_id}",
            json={
                "variants": [
                    {"label": "Randstreifen", "values": ["35 cm"]},
                    {"label": "Farbe", "values": ["rot", "blau"]},
                ],
            },
        )
        assert updated.status_code == 200
        body = updated.get_json()
        assert len(body["variants"]) == 2

        piece_row = client.get(f"/api/inventories/{inv_a}/pieces").get_json()[0]
        assert piece_row["variant"] == {"Randstreifen": "35 cm"}
        piece_id = piece_row["id"]

        saved = client.patch(
            f"/api/pieces/{piece_id}",
            json={
                "materialTypeId": type_id,
                "name": "P1",
                "variant": {"Randstreifen": "35 cm", "Farbe": "rot"},
            },
        )
        assert saved.status_code == 200
        assert saved.get_json()["variant"] == {
            "Randstreifen": "35 cm",
            "Farbe": "rot",
        }

        other = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={"name": "Jurtenplane", "tracking": "piece", "variants": []},
        )
        assert other.status_code == 201
        moved = client.patch(
            f"/api/pieces/{piece_id}",
            json={"materialTypeId": other.get_json()["id"], "name": "P1"},
        )
        assert moved.status_code == 400
        assert moved.get_json()["error"] == "material_type_locked"
    finally:
        tmp.cleanup()
