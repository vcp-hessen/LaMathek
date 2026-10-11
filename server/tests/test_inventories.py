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
            upsert_user_from_oidc(
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
            upsert_user_from_oidc(
                session,
                sub="ver",
                name="VER",
                email=None,
                force_superuser=False,
            )
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

        settings = client.get("/api/settings")
        assert settings.status_code == 200
        assert "MW" in settings.get_json()["contentResponsible"]

        _login(client, "ver")
        assert client.get("/api/inventories").get_json() == []
        assert client.get(f"/api/inventories/{inv_id}").status_code == 403
    finally:
        tmp.cleanup()


def test_plain_user_cannot_create_inventory():
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
            session.commit()

        client = app.test_client()
        _login(client, "ver")
        assert client.post("/api/inventories", json={"name": "X"}).status_code == 403
    finally:
        tmp.cleanup()


def test_materialwart_can_grant_inventory_permission():
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
            mw = upsert_user_from_oidc(
                session,
                sub="mw",
                name="MW",
                email=None,
                force_superuser=False,
            )
            colleague = upsert_user_from_oidc(
                session,
                sub="col",
                name="Colleague",
                email="col@example.org",
                force_superuser=False,
            )
            session.commit()
            mw_id = mw.id
            col_id = colleague.id

        client = app.test_client()
        _login(client, "su")
        inv_id = client.post("/api/inventories", json={"name": "Donnerskopf"}).get_json()["id"]
        client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mw_id]},
        )

        _login(client, "mw")
        updated = client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mw_id, col_id]},
        )
        assert updated.status_code == 200
        body = updated.get_json()
        assert col_id in body["userIds"]
        assert any(u["id"] == col_id for u in body["users"])

        search = client.get("/api/users/search", query_string={"q": "Colleague"})
        assert search.status_code == 200
        assert any(u["id"] == col_id for u in search.get_json())

        other_inv = client.post("/api/inventories", json={"name": "Other"})
        assert other_inv.status_code == 403
    finally:
        tmp.cleanup()


def test_cannot_clear_permissions_without_superuser():
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
            mw = upsert_user_from_oidc(
                session,
                sub="mw",
                name="MW",
                email=None,
                force_superuser=False,
            )
            session.commit()
            mw_id = mw.id

        client = app.test_client()
        _login(client, "su")
        inv_id = client.post("/api/inventories", json={"name": "Donnerskopf"}).get_json()["id"]
        client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": [mw_id]},
        )

        with app.app_context():
            from sqlalchemy import select

            session = get_session()
            su_row = session.scalar(select(User).where(User.oidc_sub == "su"))
            assert su_row is not None
            su_row.is_superuser = False
            session.commit()

        _login(client, "mw")
        cleared = client.put(
            f"/api/inventories/{inv_id}/permissions",
            json={"userIds": []},
        )
        assert cleared.status_code == 409
        assert cleared.get_json()["error"] == "cannot_clear_permissions"
    finally:
        tmp.cleanup()
