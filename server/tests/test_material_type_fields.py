from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def _setup_inventories(client):
    _login(client, "su")
    a = client.post("/api/inventories", json={"name": "A"})
    b = client.post("/api/inventories", json={"name": "B"})
    assert a.status_code == 201 and b.status_code == 201
    return a.get_json()["id"], b.get_json()["id"]


def test_material_type_extended_fields_and_category():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            session.commit()

        client = app.test_client()
        inv_a, inv_b = _setup_inventories(client)

        created = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Heringe",
                "tracking": "stock",
                "shortName": "HER",
                "description": "Zelt-Heringe",
                "unit": "Stück",
                "consumable": True,
                "categoryName": "Zelt",
                "variants": [],
            },
        )
        assert created.status_code == 201
        body = created.get_json()
        assert body["shortName"] == "HER"
        assert body["description"] == "Zelt-Heringe"
        assert body["unit"] == "Stück"
        assert body["consumable"] is True
        assert body["categoryName"] == "Zelt"
        category_id = body["categoryId"]

        second = client.post(
            f"/api/inventories/{inv_b}/material-types",
            json={
                "name": "Seile",
                "tracking": "stock",
                "categoryId": category_id,
                "variants": [],
            },
        )
        assert second.status_code == 201
        assert second.get_json()["categoryId"] == category_id

        categories = client.get("/api/categories")
        assert categories.status_code == 200
        names = [c["name"] for c in categories.get_json()]
        assert names.count("Zelt") == 1

        again = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Planen",
                "tracking": "stock",
                "categoryName": "Zelt",
                "variants": [],
            },
        )
        assert again.status_code == 201
        assert again.get_json()["categoryId"] == category_id

        without_category = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Schnüre",
                "tracking": "stock",
                "categoryId": None,
                "variants": [],
            },
        )
        assert without_category.status_code == 201
        assert without_category.get_json()["categoryId"] is None

        piece_type = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Plane",
                "tracking": "piece",
                "unit": "Stück",
                "variants": [],
            },
        )
        assert piece_type.status_code == 400
        assert piece_type.get_json()["error"] == "unit_not_for_piece"
    finally:
        tmp.cleanup()
