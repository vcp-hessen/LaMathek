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


def _verantwortliche_id(client) -> int:
    with client.application.app_context():
        session = get_session()
        user = upsert_user_from_oidc(
            session, sub="ver", name="Ver", email=None, force_superuser=False
        )
        return user.id


def test_permanent_loan_create_hand_out_blocks_piece():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            session.commit()
        ver_id = _verantwortliche_id(app.test_client())
        client = app.test_client()
        inv_id = _setup_inventory(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Brettspiel", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        piece_id = piece.get_json()["id"]

        created = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={
                "groupName": "Stamm Lang",
                "responsibleUserId": ver_id,
                "kind": "permanent",
            },
        )
        assert created.status_code == 201
        body = created.get_json()
        assert body["kind"] == "permanent"

        loan_id = body["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})
        assert client.post(f"/api/loans/{loan_id}/hand-out").status_code == 200

        loan_b = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm B", "responsibleUserId": ver_id},
        )
        loan_b_id = loan_b.get_json()["id"]
        conflict = client.post(f"/api/loans/{loan_b_id}/lines", json={"pieceId": piece_id})
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"
    finally:
        tmp.cleanup()
