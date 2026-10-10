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


def _create_and_hand_out_piece_loan(client, inv_id: int, ver_id: int, piece_id: int):
    loan = client.post(
        f"/api/inventories/{inv_id}/loans",
        json={"groupName": "Stamm A", "responsibleUserId": ver_id},
    )
    loan_id = loan.get_json()["id"]
    client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})
    client.post(f"/api/loans/{loan_id}/hand-out")
    return loan_id


def test_partial_stock_return_keeps_remainder_loaned():
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
            json={"name": "Heringe", "tracking": "stock"},
        )
        type_id = mt.get_json()["id"]
        client.post(f"/api/inventories/{inv_id}/stocks/{type_id}/lots", json={"quantity": 10})

        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm A", "responsibleUserId": ver_id},
        )
        loan_id = loan.get_json()["id"]
        client.post(
            f"/api/loans/{loan_id}/lines",
            json={"materialTypeId": type_id, "quantity": 5},
        )
        client.post(f"/api/loans/{loan_id}/hand-out")

        detail = client.get(f"/api/loans/{loan_id}").get_json()
        line_id = detail["lines"][0]["id"]

        ret = client.post(
            f"/api/loans/{loan_id}/returns",
            json={
                "recordedOn": "2026-10-08",
                "entries": [{"loanLineId": line_id, "outcome": "returned", "quantity": 2}],
            },
        )
        assert ret.status_code == 201
        body = ret.get_json()
        assert body["status"] == "handed_out"
        assert body["lines"][0]["outstandingQuantity"] == 3

        loan_b = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm B", "responsibleUserId": ver_id},
        )
        loan_b_id = loan_b.get_json()["id"]
        client.post(
            f"/api/loans/{loan_b_id}/lines",
            json={"materialTypeId": type_id, "quantity": 8},
        )
        conflict = client.post(f"/api/loans/{loan_b_id}/hand-out")
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "over_loaned"
    finally:
        tmp.cleanup()


def test_full_piece_return_frees_piece():
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
        loan_id = _create_and_hand_out_piece_loan(client, inv_id, ver_id, piece_id)
        line_id = client.get(f"/api/loans/{loan_id}").get_json()["lines"][0]["id"]

        assert (
            client.post(
                f"/api/loans/{loan_id}/returns",
                json={
                    "recordedOn": "2026-10-08",
                    "entries": [{"loanLineId": line_id, "outcome": "returned"}],
                },
            ).status_code
            == 201
        )

        loan_b = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm B", "responsibleUserId": ver_id},
        )
        loan_b_id = loan_b.get_json()["id"]
        assert (
            client.post(f"/api/loans/{loan_b_id}/lines", json={"pieceId": piece_id}).status_code
            == 201
        )
        assert client.post(f"/api/loans/{loan_b_id}/hand-out").status_code == 200

        closed = client.get(f"/api/loans/{loan_id}").get_json()
        assert closed["status"] == "closed"
    finally:
        tmp.cleanup()


def test_piece_loss_blocks_reissue_and_stock_loss_reduces_quantity():
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

        mt_piece = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        piece_type_id = mt_piece.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": piece_type_id, "name": "P1"},
        )
        piece_id = piece.get_json()["id"]
        loan_piece_id = _create_and_hand_out_piece_loan(client, inv_id, ver_id, piece_id)
        line_id = client.get(f"/api/loans/{loan_piece_id}").get_json()["lines"][0]["id"]
        client.post(
            f"/api/loans/{loan_piece_id}/returns",
            json={
                "recordedOn": "2026-10-08",
                "entries": [{"loanLineId": line_id, "outcome": "loss"}],
            },
        )

        loan_b = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm B", "responsibleUserId": ver_id},
        )
        loan_b_id = loan_b.get_json()["id"]
        conflict = client.post(f"/api/loans/{loan_b_id}/lines", json={"pieceId": piece_id})
        assert conflict.status_code == 409

        mt_stock = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        stock_type_id = mt_stock.get_json()["id"]
        client.post(
            f"/api/inventories/{inv_id}/stocks/{stock_type_id}/lots", json={"quantity": 6}
        )

        loan_stock = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm C", "responsibleUserId": ver_id},
        )
        loan_stock_id = loan_stock.get_json()["id"]
        client.post(
            f"/api/loans/{loan_stock_id}/lines",
            json={"materialTypeId": stock_type_id, "quantity": 4},
        )
        client.post(f"/api/loans/{loan_stock_id}/hand-out")
        stock_line_id = client.get(f"/api/loans/{loan_stock_id}").get_json()["lines"][0]["id"]
        client.post(
            f"/api/loans/{loan_stock_id}/returns",
            json={
                "recordedOn": "2026-10-09",
                "entries": [
                    {"loanLineId": stock_line_id, "outcome": "loss", "quantity": 2}
                ],
            },
        )
        stock = client.get(f"/api/inventories/{inv_id}/stocks").get_json()
        row = next(r for r in stock if r["materialTypeId"] == stock_type_id)
        assert row["quantity"] == 4
    finally:
        tmp.cleanup()


def test_over_return_rejected():
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
            json={"name": "Heringe", "tracking": "stock"},
        )
        type_id = mt.get_json()["id"]
        client.post(f"/api/inventories/{inv_id}/stocks/{type_id}/lots", json={"quantity": 5})

        loan = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Stamm A", "responsibleUserId": ver_id},
        )
        loan_id = loan.get_json()["id"]
        client.post(
            f"/api/loans/{loan_id}/lines",
            json={"materialTypeId": type_id, "quantity": 3},
        )
        client.post(f"/api/loans/{loan_id}/hand-out")
        line_id = client.get(f"/api/loans/{loan_id}").get_json()["lines"][0]["id"]

        client.post(
            f"/api/loans/{loan_id}/returns",
            json={
                "recordedOn": "2026-10-08",
                "entries": [{"loanLineId": line_id, "outcome": "returned", "quantity": 2}],
            },
        )
        over = client.post(
            f"/api/loans/{loan_id}/returns",
            json={
                "recordedOn": "2026-10-09",
                "entries": [{"loanLineId": line_id, "outcome": "returned", "quantity": 2}],
            },
        )
        assert over.status_code == 409
        assert over.get_json()["error"] == "over_returned"
    finally:
        tmp.cleanup()


def test_returns_forbidden_without_inventory_access():
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
        loan_id = _create_and_hand_out_piece_loan(client, inv_id, ver_id, piece_id)
        line_id = client.get(f"/api/loans/{loan_id}").get_json()["lines"][0]["id"]

        _login(client, "other")
        forbidden = client.post(
            f"/api/loans/{loan_id}/returns",
            json={
                "recordedOn": "2026-10-08",
                "entries": [{"loanLineId": line_id, "outcome": "returned"}],
            },
        )
        assert forbidden.status_code == 403
    finally:
        tmp.cleanup()
