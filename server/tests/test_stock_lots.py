import os
import tempfile

from lamathek.app import create_app
from lamathek.config import Config
from lamathek.db import get_session
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
        from lamathek.db import Base, engine

        Base.metadata.create_all(engine)
        get_installation_settings(get_session())
    return app, tmp


def _login(client):
    with client.session_transaction() as sess:
        sess["user"] = {"sub": "su", "name": "SU", "email": None}


def test_stock_lots_sum_and_variant():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            upsert_user_from_oidc(
                get_session(), sub="su", name="SU", email=None, force_superuser=True
            )
        client = app.test_client()
        _login(client)
        inv_id = client.post("/api/inventories", json={"name": "Lager"}).get_json()["id"]
        created = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={
                "name": "Heringe",
                "tracking": "stock",
                "variants": [{"label": "Länge", "values": ["30 cm", "40 cm"]}],
            },
        )
        type_id = created.get_json()["id"]
        first = client.post(
            f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
            json={"label": "Kiste I", "variant": {"Länge": "30 cm"}, "quantity": 20},
        )
        assert first.status_code == 201
        second = client.post(
            f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
            json={"label": "Kiste II", "variant": {"Länge": "40 cm"}, "quantity": 15},
        )
        assert second.status_code == 201
        row = second.get_json()
        assert row["quantity"] == 35
        assert len(row["lots"]) == 2

        bad = client.post(
            f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
            json={"variant": {"Länge": "99 cm"}, "quantity": 1},
        )
        assert bad.status_code == 400
        assert bad.get_json()["error"] == "invalid_variant"
    finally:
        tmp.cleanup()
