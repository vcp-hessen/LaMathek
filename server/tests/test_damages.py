import os
import tempfile

from lamathek.app import create_app
from lamathek.config import Config
from lamathek import db
from lamathek.db import Base, get_session
from lamathek.services.inventories import ROLE_VERANTWORTLICHE
from lamathek.services.settings import get_installation_settings
from lamathek.services.users import set_user_role, upsert_user_from_oidc


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
        set_user_role(session, user, ROLE_VERANTWORTLICHE)
        session.commit()
        return user.id


def _piece_id(client, inv_id: int) -> int:
    mt = client.post(
        f"/api/inventories/{inv_id}/material-types",
        json={"name": "Plane", "tracking": "piece"},
    )
    type_id = mt.get_json()["id"]
    piece = client.post(
        f"/api/inventories/{inv_id}/pieces",
        json={"materialTypeId": type_id, "name": "P1"},
    )
    return piece.get_json()["id"]


def test_severe_open_damage_blocks_piece_and_set_handout():
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
        piece_id = _piece_id(client, inv_id)

        loan_piece = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm A", "responsibleUserId": ver_id},
        )
        loan_piece_id = loan_piece.get_json()["id"]
        client.post(f"/api/loans/{loan_piece_id}/lines", json={"pieceId": piece_id})

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )
        loan_set = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm B", "responsibleUserId": ver_id},
        )
        loan_set_id = loan_set.get_json()["id"]
        client.post(f"/api/loans/{loan_set_id}/lines", json={"setId": set_id})

        damage = client.post(
            f"/api/pieces/{piece_id}/damages",
            json={"recordedOn": "2026-10-09", "severe": True, "note": "Riss"},
        )
        assert damage.status_code == 201

        conflict = client.post(f"/api/loans/{loan_piece_id}/hand-out")
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"

        conflict_set = client.post(f"/api/loans/{loan_set_id}/hand-out")
        assert conflict_set.status_code == 409
        assert conflict_set.get_json()["error"] == "piece_unavailable"
    finally:
        tmp.cleanup()


def test_repair_allows_handout_again():
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
        piece_id = _piece_id(client, inv_id)

        damage = client.post(
            f"/api/pieces/{piece_id}/damages",
            json={"recordedOn": "2026-10-09", "severe": True},
        )
        damage_id = damage.get_json()["id"]
        assert (
            client.post(
                f"/api/damages/{damage_id}/repairs",
                json={"recordedOn": "2026-10-10"},
            ).status_code
            == 201
        )

        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm A", "responsibleUserId": ver_id},
        )
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})
        assert client.post(f"/api/loans/{loan_id}/hand-out").status_code == 200
    finally:
        tmp.cleanup()


def test_non_severe_damage_does_not_block():
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
        piece_id = _piece_id(client, inv_id)

        assert (
            client.post(
                f"/api/pieces/{piece_id}/damages",
                json={"recordedOn": "2026-10-09", "severe": False},
            ).status_code
            == 201
        )

        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm A", "responsibleUserId": ver_id},
        )
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})
        assert client.post(f"/api/loans/{loan_id}/hand-out").status_code == 200
    finally:
        tmp.cleanup()


def test_second_repair_rejected():
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
        piece_id = _piece_id(client, inv_id)

        damage = client.post(
            f"/api/pieces/{piece_id}/damages",
            json={"recordedOn": "2026-10-09", "severe": True},
        )
        damage_id = damage.get_json()["id"]
        client.post(
            f"/api/damages/{damage_id}/repairs",
            json={"recordedOn": "2026-10-10"},
        )
        again = client.post(
            f"/api/damages/{damage_id}/repairs",
            json={"recordedOn": "2026-10-11"},
        )
        assert again.status_code == 409
        assert again.get_json()["error"] == "already_repaired"
    finally:
        tmp.cleanup()


def test_damage_forbidden_without_inventory_access():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )
            upsert_user_from_oidc(
                session, sub="other", name="Other", email=None, force_superuser=False
            )
            session.commit()
        client = app.test_client()
        inv_id = _setup_inventory(client)
        piece_id = _piece_id(client, inv_id)

        _login(client, "other")
        forbidden = client.post(
            f"/api/pieces/{piece_id}/damages",
            json={"recordedOn": "2026-10-09", "severe": False},
        )
        assert forbidden.status_code == 403
    finally:
        tmp.cleanup()
