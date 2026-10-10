import os
import tempfile

from lamathek.app import create_app
from lamathek.config import Config
from lamathek import db
from lamathek.db import Base, get_session
from lamathek.services.settings import get_installation_settings
from lamathek.services.users import upsert_user_from_oidc


def _app_with_db():
    tmp = tempfile.TemporaryDirectory()
    db_path = os.path.join(tmp.name, "test.sqlite3")

    class TestConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        TESTING = True

    app = create_app(TestConfig)
    with app.app_context():
        Base.metadata.create_all(db.engine)
        get_installation_settings(get_session())
    return app, tmp


def _login(client, sub: str):
    with client.session_transaction() as sess:
        sess["user"] = {"sub": sub, "name": sub, "email": None}


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
                "variantValues": [],
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
                "variantValues": [],
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
                "variantValues": [],
            },
        )
        assert again.status_code == 201
        assert again.get_json()["categoryId"] == category_id

        piece_type = client.post(
            f"/api/inventories/{inv_a}/material-types",
            json={
                "name": "Plane",
                "tracking": "piece",
                "unit": "Stück",
                "variantValues": [],
            },
        )
        assert piece_type.status_code == 400
        assert piece_type.get_json()["error"] == "unit_not_for_piece"
    finally:
        tmp.cleanup()
