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
            json={"name": "Brettspiel", "tracking": "piece", "variantValues": []},
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
                "variantLabel": "Randstreifen",
                "variantValues": ["0 cm", "35 cm"],
            },
        )
        assert plane.status_code == 201
        type_id = plane.get_json()["id"]

        bad = client.post(
            f"/api/inventories/{inv_a}/pieces",
            json={"materialTypeId": type_id, "name": "P1", "variant": "99 cm"},
        )
        assert bad.status_code == 400
        assert bad.get_json()["error"] == "invalid_variant"

        good = client.post(
            f"/api/inventories/{inv_a}/pieces",
            json={"materialTypeId": type_id, "name": "P1", "variant": "35 cm"},
        )
        assert good.status_code == 201
    finally:
        tmp.cleanup()
