from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login
from loan_helpers import (
    add_piece_line,
    borrower_id,
    confirm_all_lines,
    create_loan,
    manager_id,
    setup_inventory,
    submit_request,
)


def _bootstrap(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        session.commit()


def test_add_set_creates_lines():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)

        mt_plane = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        plane_type = mt_plane.get_json()["id"]
        plane = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": plane_type, "name": "P1"},
        ).get_json()["id"]

        set_res = client.post(
            f"/api/inventories/{inv_id}/sets",
            json={"name": "Jurte"},
        )
        set_id = set_res.get_json()["id"]
        client.put(
            f"/api/sets/{set_id}/pieces",
            json={"pieceId": plane, "role": "assignment"},
        )

        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        add = client.post(
            f"/api/loans/{loan_id}/lines",
            json={"setId": set_id, "scope": "assignment"},
        )
        assert add.status_code == 201
        detail = add.get_json()
        assert len(detail["lines"]) >= 1
        submit_request(client, loan_id)
        _login(client, "mgr")
        line_ids = [line["id"] for line in detail["lines"]]
        assert confirm_all_lines(client, loan_id, mgr_id, line_ids).status_code == 200
    finally:
        tmp.cleanup()


def test_add_set_includes_pieces_that_are_not_in_the_box_yet():
    app, tmp = _app_with_db()
    try:
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        first = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "P1"},
        ).get_json()["id"]
        second = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "P2"},
        ).get_json()["id"]
        set_id = client.post(
            f"/api/inventories/{inv_id}/sets",
            json={"name": "Jurte"},
        ).get_json()["id"]
        for piece_id in (first, second):
            placed = client.put(
                f"/api/sets/{set_id}/pieces",
                json={"pieceId": piece_id, "role": "assignment"},
            )
            assert placed.status_code == 200

        loan_id = create_loan(client, inv_id, bor_id).get_json()["id"]
        alone = add_piece_line(client, loan_id, first)
        assert alone.status_code == 201
        existing_id = next(
            line["id"]
            for line in alone.get_json()["lines"]
            if line["pieceId"] == first
        )

        added = client.post(
            f"/api/loans/{loan_id}/lines",
            json={"setId": set_id, "scope": "assignment"},
        )
        assert added.status_code == 201, added.get_json()
        lines = added.get_json()["lines"]
        by_piece = {line["pieceId"]: line for line in lines}
        assert set(by_piece) == {first, second}
        assert by_piece[first]["id"] == existing_id
        assert by_piece[second]["status"] == "draft"
    finally:
        tmp.cleanup()
