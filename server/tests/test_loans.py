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


def _create_loan(client, inv_id: int, ver_id: int):
    return client.post(
        f"/api/inventories/{inv_id}/loans",
        json={"groupName": "Stamm A", "responsibleUserId": ver_id},
    )


def test_piece_cannot_be_handed_out_twice():
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

        loan_a = _create_loan(client, inv_id, ver_id)
        loan_b = _create_loan(client, inv_id, ver_id)
        loan_a_id = loan_a.get_json()["id"]
        loan_b_id = loan_b.get_json()["id"]

        assert (
            client.post(f"/api/loans/{loan_a_id}/lines", json={"pieceId": piece_id}).status_code
            == 201
        )
        assert (
            client.post(f"/api/loans/{loan_b_id}/lines", json={"pieceId": piece_id}).status_code
            == 201
        )
        assert client.post(f"/api/loans/{loan_a_id}/hand-out").status_code == 200

        conflict = client.post(f"/api/loans/{loan_b_id}/hand-out")
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"
    finally:
        tmp.cleanup()


def test_planned_loan_does_not_block_piece_on_another_planned():
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

        loan_a = _create_loan(client, inv_id, ver_id)
        loan_b = _create_loan(client, inv_id, ver_id)
        loan_a_id = loan_a.get_json()["id"]
        loan_b_id = loan_b.get_json()["id"]

        assert (
            client.post(f"/api/loans/{loan_a_id}/lines", json={"pieceId": piece_id}).status_code
            == 201
        )
        ok = client.post(f"/api/loans/{loan_b_id}/lines", json={"pieceId": piece_id})
        assert ok.status_code == 201
    finally:
        tmp.cleanup()


def test_set_hand_out_blocked_when_assignment_piece_out():
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
            json={"name": "Plane", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "P1"},
        )
        piece_id = piece.get_json()["id"]

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )

        loan_piece = _create_loan(client, inv_id, ver_id)
        loan_piece_id = loan_piece.get_json()["id"]
        client.post(f"/api/loans/{loan_piece_id}/lines", json={"pieceId": piece_id})
        client.post(f"/api/loans/{loan_piece_id}/hand-out")

        loan_set = _create_loan(client, inv_id, ver_id)
        loan_set_id = loan_set.get_json()["id"]
        conflict = client.post(f"/api/loans/{loan_set_id}/lines", json={"setId": set_id})
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"
    finally:
        tmp.cleanup()


def test_stock_hand_out_cannot_exceed_available():
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

        heringe = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        type_id = heringe.get_json()["id"]
        client.post(f"/api/inventories/{inv_id}/stocks/{type_id}/lots", json={"quantity": 5})

        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]
        client.post(
            f"/api/loans/{loan_id}/lines",
            json={"materialTypeId": type_id, "quantity": 6},
        )
        conflict = client.post(f"/api/loans/{loan_id}/hand-out")
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "over_loaned"
    finally:
        tmp.cleanup()


def test_loans_forbidden_without_inventory_access():
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
        ver_id = _verantwortliche_id(app.test_client())

        client = app.test_client()
        inv_id = _setup_inventory(client)
        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]

        _login(client, "other")
        forbidden = client.get(f"/api/loans/{loan_id}")
        assert forbidden.status_code == 403
    finally:
        tmp.cleanup()
