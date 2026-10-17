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

        from loan_helpers import create_loan

        loan_piece = create_loan(client, inv_id, ver_id, groupName="Stamm A")
        loan_piece_id = loan_piece.get_json()["id"]
        client.post(f"/api/loans/{loan_piece_id}/lines", json={"pieceId": piece_id})
        _login(client, "su")

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        set_id = material_set.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": piece_id, "role": "assignment"},
        )
        from loan_helpers import borrower_id, create_loan

        ver2_id = borrower_id(client, sub="ver2")
        loan_set = create_loan(client, inv_id, ver2_id, groupName="Stamm B")
        loan_set_id = loan_set.get_json()["id"]
        client.post(
            f"/api/loans/{loan_set_id}/lines",
            json={"setId": set_id, "scope": "assignment"},
        )
        _login(client, "su")

        damage = client.post(
            f"/api/pieces/{piece_id}/damages",
            json={"recordedOn": "2026-10-09", "severe": True, "note": "Riss"},
        )
        assert damage.status_code == 201

        from loan_helpers import confirm_all_lines, manager_id, submit_request

        mgr_id = manager_id(client)
        with client.application.app_context():
            session = get_session()
            u = session.get(__import__("lamathek.models.user", fromlist=["User"]).User, ver_id)
            u.phone = "+49123"
            session.commit()
        _login(client, "ver")
        submit_request(client, loan_piece_id)
        _login(client, "su")
        lines = client.get(f"/api/loans/{loan_piece_id}").get_json()["lines"]
        conflict = confirm_all_lines(
            client, loan_piece_id, mgr_id, [lines[0]["id"]]
        )
        assert conflict.status_code == 409
        assert conflict.get_json()["error"] == "piece_unavailable"

        _login(client, "ver2")
        submit_request(client, loan_set_id)
        _login(client, "su")
        lines_set = client.get(f"/api/loans/{loan_set_id}").get_json()["lines"]
        conflict_set = confirm_all_lines(
            client, loan_set_id, mgr_id, [l["id"] for l in lines_set]
        )
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

        from loan_helpers import confirm_all_lines, create_loan, manager_id, submit_request

        loan = create_loan(client, inv_id, ver_id, groupName="Stamm A")
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})

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

        from loan_helpers import confirm_all_lines, create_loan, manager_id, submit_request

        loan = create_loan(client, inv_id, ver_id, groupName="Stamm A")
        loan_id = loan.get_json()["id"]
        client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})

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
