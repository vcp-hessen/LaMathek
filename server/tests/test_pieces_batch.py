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


def _setup_inventory(client):
    _login(client, "su")
    inv = client.post("/api/inventories", json={"name": "Donnerskopf"})
    assert inv.status_code == 201
    return inv.get_json()["id"]


def test_batch_pieces_on_existing_set():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Vierecksplane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets",
            json={"name": "Jurte 3", "shortName": "J3"},
        )
        assert material_set.status_code == 201
        set_id = material_set.get_json()["id"]

        batch = client.post(
            f"/api/inventories/{inv_id}/pieces/batch",
            json={
                "materialTypeId": plane_id,
                "count": 3,
                "namePattern": "J3-{n}",
                "setId": set_id,
            },
        )
        assert batch.status_code == 201
        body = batch.get_json()
        assert body["setId"] == set_id
        assert len(body["pieces"]) == 3
        assert body["pieces"][0]["name"] == "J3-1"
        assert all(p["setId"] == set_id for p in body["pieces"])
    finally:
        tmp.cleanup()


def test_batch_pieces_with_new_set():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Kohtenplane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]

        batch = client.post(
            f"/api/inventories/{inv_id}/pieces/batch",
            json={
                "materialTypeId": plane_id,
                "count": 2,
                "namePattern": "K-{n}",
                "setName": "Kohte A",
                "setShortName": "KA",
            },
        )
        assert batch.status_code == 201
        body = batch.get_json()
        assert body["setId"] is not None
        assert len(body["pieces"]) == 2
    finally:
        tmp.cleanup()


def test_batch_rejects_set_id_and_name_together():
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
        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]

        batch = client.post(
            f"/api/inventories/{inv_id}/pieces/batch",
            json={
                "materialTypeId": plane_id,
                "count": 1,
                "namePattern": "X-{n}",
                "setId": 1,
                "setName": "New",
            },
        )
        assert batch.status_code == 400
        assert batch.get_json()["error"] == "set_conflict"
    finally:
        tmp.cleanup()


def test_batch_requires_n_placeholder_in_pattern():
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
        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]

        batch = client.post(
            f"/api/inventories/{inv_id}/pieces/batch",
            json={
                "materialTypeId": plane_id,
                "count": 2,
                "namePattern": "J3",
            },
        )
        assert batch.status_code == 400
        assert batch.get_json()["error"] == "invalid_name_pattern"
    finally:
        tmp.cleanup()


def test_batch_invalid_variant_rolls_back():
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
            json={
                "name": "Plane",
                "tracking": "piece",
                "variantLabel": "Rand",
                "variantValues": ["0 cm"],
            },
        )
        plane_id = mt.get_json()["id"]

        batch = client.post(
            f"/api/inventories/{inv_id}/pieces/batch",
            json={
                "materialTypeId": plane_id,
                "count": 2,
                "namePattern": "P-{n}",
                "variant": "99 cm",
            },
        )
        assert batch.status_code == 400

        listed = client.get(f"/api/inventories/{inv_id}/pieces")
        assert listed.get_json() == []
    finally:
        tmp.cleanup()
