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


def _seed_users(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        mw = upsert_user_from_oidc(
            session, sub="mw", name="MW", email=None, force_superuser=False
        )
        mw.role = "materialwart"
        session.commit()
        return mw.id


def test_superuser_deletes_inventory_and_material_type_materialwart_forbidden():
    app, tmp = _app_with_db()
    try:
        mw_id = _seed_users(app)
        client = app.test_client()
        _login(client, "su")
        inv = client.post("/api/inventories", json={"name": "Testinv"})
        assert inv.status_code == 201
        inv_id = inv.get_json()["id"]
        client.put(f"/api/inventories/{inv_id}/permissions", json={"userIds": [mw_id]})

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        assert mt.status_code == 201
        mt_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt_id, "name": "P1"},
        )
        assert piece.status_code == 201

        _login(client, "mw")
        assert client.delete(f"/api/inventories/{inv_id}").status_code == 403
        assert client.delete(f"/api/material-types/{mt_id}").status_code == 403
        assert client.delete(f"/api/pieces/{piece.get_json()['id']}").status_code == 403

        _login(client, "su")
        assert client.delete(f"/api/material-types/{mt_id}").status_code == 204
        listed = client.get(f"/api/inventories/{inv_id}/material-types")
        assert listed.status_code == 200
        assert listed.get_json() == []

        assert client.delete(f"/api/inventories/{inv_id}").status_code == 204
        assert client.get("/api/inventories").get_json() == []
    finally:
        tmp.cleanup()
