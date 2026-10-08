import os
import tempfile

from lamathek.app import create_app
from lamathek.config import Config
from lamathek import db
from lamathek.db import Base, get_session
from lamathek.models.user import User
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


def test_materialwart_sees_only_permitted_inventories():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            superuser = upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            mw = upsert_user_from_oidc(
                session,
                sub="mw",
                name="MW",
                email=None,
                force_superuser=False,
            )
            mw.role = "materialwart"
            ver = upsert_user_from_oidc(
                session,
                sub="ver",
                name="VER",
                email=None,
                force_superuser=False,
            )
            ver.role = "verantwortliche"
            session.commit()
            mw_id = mw.id

        client = app.test_client()
        _login(client, "su")
        created = client.post("/api/inventories", json={"name": "Donnerskopf"})
        assert created.status_code == 201
        inv_id = created.get_json()["id"]

        other = client.post("/api/inventories", json={"name": "Landesbüro"})
        assert other.status_code == 201
        other_id = other.get_json()["id"]

        client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mw_id]},
        )

        _login(client, "mw")
        listed = client.get("/api/inventories")
        assert listed.status_code == 200
        names = [i["name"] for i in listed.get_json()]
        assert names == ["Donnerskopf"]

        denied = client.get(f"/api/inventories/{other_id}")
        assert denied.status_code == 403

        renamed = client.patch(
            f"/api/inventories/{inv_id}",
            json={"name": "Donnerskopf (Mat)"},
        )
        assert renamed.status_code == 200

        _login(client, "ver")
        assert client.get("/api/inventories").get_json() == []
        assert client.get(f"/api/inventories/{inv_id}").status_code == 403
    finally:
        tmp.cleanup()


def test_verantwortliche_cannot_create_inventory():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="ver",
                name="VER",
                email=None,
                force_superuser=False,
            )
            from sqlalchemy import select

            user = session.scalar(select(User).where(User.oidc_sub == "ver"))
            user.role = "verantwortliche"
            session.commit()

        client = app.test_client()
        _login(client, "ver")
        assert client.post("/api/inventories", json={"name": "X"}).status_code == 403
    finally:
        tmp.cleanup()
