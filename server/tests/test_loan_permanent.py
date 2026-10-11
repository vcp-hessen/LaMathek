from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


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
