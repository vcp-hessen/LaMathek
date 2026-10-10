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


def _create_loan(client, inv_id, ver_id, **extra):
    payload = {
        "groupName": "Gruppe",
        "responsibleUserId": ver_id,
        **extra,
    }
    return client.post(f"/api/inventories/{inv_id}/loans", json=payload)


def test_add_set_creates_piece_and_stock_lines_and_hand_out():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]
        p1 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P1"},
        )
        piece_id = p1.get_json()["id"]

        heringe = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        heringe_id = heringe.get_json()["id"]
        client.put(
            f"/api/inventories/{inv_id}/stocks/{heringe_id}", json={"quantity": 20}
        )

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )
        client.put(
            f"/api/sets/{set_id}/stock-lines",
            json={"materialTypeId": heringe_id, "role": "assignment", "quantity": 5},
        )

        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]
        add = client.post(f"/api/loans/{loan_id}/lines", json={"setId": set_id})
        assert add.status_code == 201
        detail = add.get_json()
        kinds = {ln["kind"] for ln in detail["lines"]}
        assert kinds == {"piece", "stock"}
        assert all(ln["originSetId"] == set_id for ln in detail["lines"])
        assert all(ln["originSetRole"] == "assignment" for ln in detail["lines"])

        hand = client.post(f"/api/loans/{loan_id}/hand-out")
        assert hand.status_code == 200
        assert hand.get_json()["status"] == "handed_out"
    finally:
        tmp.cleanup()


def test_changing_set_assignment_does_not_change_loan():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]
        p1 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P1"},
        )
        p2 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P2"},
        )
        piece_id = p1.get_json()["id"]
        piece2_id = p2.get_json()["id"]

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )

        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"setId": set_id})
        before = client.get(f"/api/loans/{loan_id}").get_json()
        piece_lines = [ln for ln in before["lines"] if ln["kind"] == "piece"]
        assert len(piece_lines) == 1
        assert piece_lines[0]["pieceId"] == piece_id

        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece2_id, "role": "assignment"},
        )

        after = client.get(f"/api/loans/{loan_id}").get_json()
        piece_lines_after = [ln for ln in after["lines"] if ln["kind"] == "piece"]
        assert piece_lines_after == piece_lines
    finally:
        tmp.cleanup()


def test_optional_stock_on_one_loan_not_two():
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
        heringe_id = heringe.get_json()["id"]
        client.put(
            f"/api/inventories/{inv_id}/stocks/{heringe_id}", json={"quantity": 10}
        )

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/stock-lines",
            json={"materialTypeId": heringe_id, "role": "optional", "quantity": 3},
        )

        loan_a = _create_loan(client, inv_id, ver_id)
        loan_a_id = loan_a.get_json()["id"]
        client.post(f"/api/loans/{loan_a_id}/lines", json={"setId": set_id})
        client.post(
            f"/api/loans/{loan_a_id}/lines",
            json={"setId": set_id, "scope": "optionals"},
        )
        ok = client.post(f"/api/loans/{loan_a_id}/hand-out")
        assert ok.status_code == 200

        loan_b = _create_loan(client, inv_id, ver_id)
        loan_b_id = loan_b.get_json()["id"]
        client.post(f"/api/loans/{loan_b_id}/lines", json={"setId": set_id})
        client.post(
            f"/api/loans/{loan_b_id}/lines",
            json={"setId": set_id, "scope": "optionals"},
        )
        conflict = client.post(f"/api/loans/{loan_b_id}/hand-out")
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "over_loaned"
    finally:
        tmp.cleanup()


def test_piece_loss_does_not_block_sibling_in_set_origin():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]
        p1 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P1"},
        )
        p2 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P2"},
        )
        piece1_id = p1.get_json()["id"]
        piece2_id = p2.get_json()["id"]

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece1_id, "role": "assignment"},
        )
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece2_id, "role": "assignment"},
        )

        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"setId": set_id})
        client.post(f"/api/loans/{loan_id}/hand-out")
        detail = client.get(f"/api/loans/{loan_id}").get_json()
        line1 = next(ln for ln in detail["lines"] if ln.get("pieceId") == piece1_id)
        line2 = next(ln for ln in detail["lines"] if ln.get("pieceId") == piece2_id)
        client.post(
            f"/api/loans/{loan_id}/returns",
            json={
                "recordedOn": "2026-01-01",
                "entries": [
                    {"loanLineId": line1["id"], "outcome": "loss"},
                    {"loanLineId": line2["id"], "outcome": "returned"},
                ],
            },
        )

        loan2 = _create_loan(client, inv_id, ver_id)
        loan2_id = loan2.get_json()["id"]
        add = client.post(
            f"/api/loans/{loan2_id}/lines", json={"pieceId": piece2_id}
        )
        assert add.status_code == 201
        hand = client.post(f"/api/loans/{loan2_id}/hand-out")
        assert hand.status_code == 200
    finally:
        tmp.cleanup()


def test_delete_piece_and_lower_stock_blocked():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]
        p1 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P1"},
        )
        piece_id = p1.get_json()["id"]

        heringe = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Heringe", "tracking": "stock"},
        )
        heringe_id = heringe.get_json()["id"]
        client.put(
            f"/api/inventories/{inv_id}/stocks/{heringe_id}", json={"quantity": 10}
        )

        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})
        client.post(
            f"/api/loans/{loan_id}/lines",
            json={"materialTypeId": heringe_id, "quantity": 4},
        )

        del_piece = client.delete(f"/api/pieces/{piece_id}")
        assert del_piece.status_code == 409
        assert del_piece.get_json()["error"] == "piece_on_loan"

        lower = client.put(
            f"/api/inventories/{inv_id}/stocks/{heringe_id}", json={"quantity": 0}
        )
        assert lower.status_code == 409
        assert lower.get_json()["error"] == "below_loaned"
    finally:
        tmp.cleanup()


def test_delete_set_keeps_loan_lines():
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

        plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_id = plane.get_json()["id"]
        p1 = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_id, "name": "P1"},
        )
        piece_id = p1.get_json()["id"]

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )

        loan = _create_loan(client, inv_id, ver_id)
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"setId": set_id})
        before = client.get(f"/api/loans/{loan_id}").get_json()
        assert len(before["lines"]) == 1

        assert client.delete(f"/api/sets/{set_id}").status_code == 204

        after = client.get(f"/api/loans/{loan_id}").get_json()
        assert len(after["lines"]) == 1
        assert after["lines"][0]["originSetId"] is None
        assert after["lines"][0]["pieceId"] == piece_id
    finally:
        tmp.cleanup()


def test_permanent_loan_rejects_event_and_bad_dates():
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

        bad_event = _create_loan(
            client,
            inv_id,
            ver_id,
            kind="permanent",
            eventName="Lager",
        )
        assert bad_event.status_code == 400
        assert bad_event.get_json()["error"] == "invalid_permanent_fields"

        bad_range = _create_loan(
            client,
            inv_id,
            ver_id,
            startsOn="2026-06-10",
            endsOn="2026-06-01",
        )
        assert bad_range.status_code == 400
        assert bad_range.get_json()["error"] == "invalid_date_range"
    finally:
        tmp.cleanup()
