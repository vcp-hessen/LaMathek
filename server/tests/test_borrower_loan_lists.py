from datetime import date, timedelta

from lamathek.db import get_session
from lamathek.services.inventories import create_inventory
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
from loan_helpers import borrower_id, create_loan, manager_id, setup_inventory


def _bootstrap(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        session.commit()


def test_manager_loan_list_excludes_drafts():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        _login(client, "su")
        draft_id = create_loan(client, inv_id, bor_id, groupName="Entwurf").get_json()["id"]

        _login(client, "mgr")
        rows = client.get(f"/api/inventories/{inv_id}/loans").get_json()
        assert draft_id not in {row["id"] for row in rows}
        assert client.get(f"/api/loans/{draft_id}").status_code == 403
    finally:
        tmp.cleanup()


def test_manager_loan_list_includes_own_draft():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        mgr = manager_id(client)
        _login(client, "mgr")
        created = client.post(
            f"/api/inventories/{inv_id}/loans",
            json={"groupName": "Eigener Entwurf", "borrowerUserId": mgr},
        )
        assert created.status_code == 201
        draft_id = created.get_json()["id"]
        assert created.get_json()["phase"] == "draft"

        rows = client.get(f"/api/inventories/{inv_id}/loans").get_json()
        assert draft_id in {row["id"] for row in rows}
    finally:
        tmp.cleanup()


def test_inventory_loan_list_filtered_per_borrower():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        with app.app_context():
            session = get_session()
            inv = create_inventory(session, "Public", visibility="active")
            session.commit()
            inv_id = inv.id

        bor_a = borrower_id(client, sub="borrower_a")
        bor_b = borrower_id(client, sub="borrower_b")

        _login(client, "su")
        loan_a = create_loan(client, inv_id, bor_a, groupName="Gruppe A").get_json()["id"]
        loan_b = create_loan(client, inv_id, bor_b, groupName="Gruppe B").get_json()["id"]

        _login(client, "borrower_a")
        rows_a = client.get(f"/api/inventories/{inv_id}/loans").get_json()
        assert {row["id"] for row in rows_a} == {loan_a}

        _login(client, "borrower_b")
        rows_b = client.get(f"/api/inventories/{inv_id}/loans").get_json()
        assert {row["id"] for row in rows_b} == {loan_b}
    finally:
        tmp.cleanup()


def test_me_loans_across_inventories_and_visibility():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        with app.app_context():
            session = get_session()
            public_a = create_inventory(session, "Lager A", visibility="active")
            public_b = create_inventory(session, "Lager B", visibility="active")
            internal = create_inventory(session, "Intern", visibility="internal")
            session.commit()
            pub_a_id = public_a.id
            pub_b_id = public_b.id
            internal_id = internal.id

        viewer_id = borrower_id(client, sub="viewer")
        pickup = date.today() + timedelta(days=2)
        _login(client, "su")
        internal_loan = create_loan(
            client,
            internal_id,
            viewer_id,
            groupName="Secret",
            as_borrower=False,
            grant_read=False,
            pickupOn=pickup.isoformat(),
            returnOn=(pickup + timedelta(days=3)).isoformat(),
        ).get_json()["id"]
        loan_a = create_loan(client, pub_a_id, viewer_id, groupName="A").get_json()["id"]
        loan_b = create_loan(client, pub_b_id, viewer_id, groupName="B").get_json()["id"]

        _login(client, "viewer")
        rows = client.get("/api/me/loans").get_json()
        ids = {row["id"] for row in rows}
        assert loan_a in ids
        assert loan_b in ids
        assert internal_loan in ids
        names = {row["id"]: row["inventoryName"] for row in rows}
        assert names[loan_a] == "Lager A"
        assert names[loan_b] == "Lager B"
    finally:
        tmp.cleanup()
