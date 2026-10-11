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


def test_superuser_assigns_inventories_per_user():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            person = upsert_user_from_oidc(
                session, sub="person", name="Person", email=None, force_superuser=False
            )
            session.commit()
            person_id = person.id

        client = app.test_client()
        _login(client, "su")
        first = client.post("/api/inventories", json={"name": "Alpha"}).get_json()["id"]
        second = client.post("/api/inventories", json={"name": "Beta"}).get_json()["id"]

        listed = client.get("/api/users")
        assert listed.status_code == 200
        row = next(user for user in listed.get_json() if user["id"] == person_id)
        assert row["inventoryIds"] == []
        assert row["isSuperuser"] is False

        granted = client.post(
            f"/api/users/{person_id}/inventories",
            json={"inventoryId": second},
        )
        assert granted.status_code == 200
        assert granted.get_json()["inventoryIds"] == [second]

        granted_again = client.post(
            f"/api/users/{person_id}/inventories",
            json={"inventoryId": first},
        )
        assert granted_again.status_code == 200
        assert granted_again.get_json()["inventoryIds"] == [first, second]

        removed = client.delete(f"/api/users/{person_id}/inventories/{second}")
        assert removed.status_code == 200
        assert removed.get_json()["inventoryIds"] == [first]

        _login(client, "person")
        denied = client.get("/api/users")
        assert denied.status_code == 403
    finally:
        tmp.cleanup()


def test_superuser_can_remove_last_explicit_assignment():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            person = upsert_user_from_oidc(
                session, sub="person", name="Person", email=None, force_superuser=False
            )
            session.commit()
            person_id = person.id

        client = app.test_client()
        _login(client, "su")
        inventory_id = client.post("/api/inventories", json={"name": "Alpha"}).get_json()[
            "id"
        ]
        client.post(
            f"/api/users/{person_id}/inventories",
            json={"inventoryId": inventory_id},
        )
        removed = client.delete(f"/api/users/{person_id}/inventories/{inventory_id}")
        assert removed.status_code == 200
        assert removed.get_json()["inventoryIds"] == []
    finally:
        tmp.cleanup()


def test_revoke_blocks_last_permission_without_superuser():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            from lamathek.services.inventories import (
                grant_inventory_permission,
                inventory_by_id,
                revoke_inventory_permission,
            )

            session = get_session()
            su = upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            person = upsert_user_from_oidc(
                session, sub="person", name="Person", email=None, force_superuser=False
            )
            session.commit()
            person_id = person.id
            su_id = su.id

        client = app.test_client()
        _login(client, "su")
        inventory_id = client.post("/api/inventories", json={"name": "Alpha"}).get_json()[
            "id"
        ]

        with app.app_context():
            from sqlalchemy import select

            session = get_session()
            person = session.get(User, person_id)
            inventory = inventory_by_id(session, inventory_id)
            assert person is not None and inventory is not None
            grant_inventory_permission(session, person, inventory)
            su_row = session.scalar(select(User).where(User.id == su_id))
            assert su_row is not None
            su_row.is_superuser = False
            session.commit()
            person = session.get(User, person_id)
            inventory = inventory_by_id(session, inventory_id)
            assert person is not None and inventory is not None
            try:
                revoke_inventory_permission(session, person, inventory)
            except ValueError as exc:
                assert str(exc) == "cannot_clear_permissions"
            else:
                raise AssertionError("expected cannot_clear_permissions")
    finally:
        tmp.cleanup()
