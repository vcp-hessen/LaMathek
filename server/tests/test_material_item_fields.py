from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def _setup_inventory(client):
    _login(client, "su")
    inv = client.post("/api/inventories", json={"name": "Lager"})
    assert inv.status_code == 201
    return inv.get_json()["id"]


def _verantwortliche_id(client) -> int:
    with client.application.app_context():
        session = get_session()
        user = upsert_user_from_oidc(
            session, sub="ver", name="Ver", email=None, force_superuser=False
        )
        return user.id


def test_piece_and_material_type_metadata_round_trip():
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

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={
                "name": "Zelt",
                "tracking": "piece",
                "manufacturer": "Vaude",
                "modelName": "Mark 3",
            },
        )
        assert mt.status_code == 201
        body = mt.get_json()
        assert body["manufacturer"] == "Vaude"
        assert body["modelName"] == "Mark 3"
        type_id = body["id"]

        created = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={
                "materialTypeId": type_id,
                "name": "Zelt 1",
                "acquiredYear": 2020,
                "note": "Ersatzstange dabei",
                "source": "Spende",
                "serialNumber": "SN-42",
                "newValueCents": 19999,
            },
        )
        assert created.status_code == 201
        piece = created.get_json()
        assert piece["acquiredYear"] == 2020
        assert piece["note"] == "Ersatzstange dabei"
        assert piece["source"] == "Spende"
        assert piece["status"] == "active"
        assert piece["serialNumber"] == "SN-42"
        assert piece["newValueCents"] == 19999

        retired = client.patch(
            f"/api/pieces/{piece['id']}",
            json={"status": "retired"},
        )
        assert retired.status_code == 200
        assert retired.get_json()["status"] == "retired"
    finally:
        tmp.cleanup()


def test_retired_piece_cannot_join_loan():
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
            json={"name": "Brett", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Catan"},
        )
        piece_id = piece.get_json()["id"]
        assert (
            client.patch(f"/api/pieces/{piece_id}", json={"status": "retired"}).status_code
            == 200
        )

        from loan_helpers import create_loan

        loan = create_loan(client, inv_id, ver_id, groupName="Stamm")
        loan_id = loan.get_json()["id"]
        conflict = client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"
    finally:
        tmp.cleanup()


def test_retired_stock_lot_excluded_from_quantity_and_retire_floor():
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

        lot_a = client.post(
            f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
            json={"quantity": 10},
        )
        assert lot_a.status_code == 201
        lot_a_id = lot_a.get_json()["lots"][0]["id"]

        lot_b = client.post(
            f"/api/inventories/{inv_id}/stocks/{type_id}/lots",
            json={"quantity": 5, "label": "Reserve"},
        )
        lot_b_id = lot_b.get_json()["lots"][1]["id"]

        stocks = client.get(f"/api/inventories/{inv_id}/stocks").get_json()[0]
        assert stocks["quantity"] == 15

        retired = client.patch(
            f"/api/inventories/{inv_id}/stock-lots/{lot_b_id}",
            json={"quantity": 5, "status": "retired"},
        )
        assert retired.status_code == 200
        stocks_after = client.get(f"/api/inventories/{inv_id}/stocks").get_json()[0]
        assert stocks_after["quantity"] == 10
        assert stocks_after["lots"][1]["status"] == "retired"

        from loan_helpers import confirm_all_lines, create_loan, manager_id, submit_request

        loan = create_loan(client, inv_id, ver_id, groupName="Stamm")
        loan_id = loan.get_json()["id"]
        assert (
            client.post(
                f"/api/loans/{loan_id}/lines",
                json={"materialTypeId": type_id, "quantity": 8},
            ).status_code
            == 201
        )
        with client.application.app_context():
            session = get_session()
            from lamathek.models.user import User

            u = session.get(User, ver_id)
            u.phone = "+49123"
            session.commit()
        mgr_id = manager_id(client)
        _login(client, "ver")
        submit_request(client, loan_id)
        _login(client, "su")
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        assert confirm_all_lines(client, loan_id, mgr_id, [lines[0]["id"]]).status_code == 200

        below = client.patch(
            f"/api/inventories/{inv_id}/stock-lots/{lot_a_id}",
            json={"quantity": 10, "status": "retired"},
        )
        assert below.status_code == 409
        assert below.get_json()["error"] == "below_loaned"
    finally:
        tmp.cleanup()
