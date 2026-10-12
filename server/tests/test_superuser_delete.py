from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def _seed_users(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        mw = upsert_user_from_oidc(
            session, sub="mw", name="MW", email=None, force_superuser=False
        )
        session.commit()
        return mw.id


def test_inventory_delete_superuser_only_materialwart_deletes_content():
    app, tmp = _app_with_db()
    try:
        mw_id = _seed_users(app)
        client = app.test_client()
        _login(client, "su")
        inv = client.post("/api/inventories", json={"name": "Testinv"})
        assert inv.status_code == 201
        inv_id = inv.get_json()["id"]
        client.put(f"/api/inventories/{inv_id}/permissions", json={"userIds": [mw_id]})

        mt_used = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Plane", "tracking": "piece"},
        )
        assert mt_used.status_code == 201
        mt_used_id = mt_used.get_json()["id"]
        mt_empty = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Leer", "tracking": "piece"},
        )
        assert mt_empty.status_code == 201
        mt_empty_id = mt_empty.get_json()["id"]

        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": mt_used_id, "name": "P1"},
        )
        assert piece.status_code == 201
        piece_id = piece.get_json()["id"]

        material_set = client.post(
            f"/api/inventories/{inv_id}/sets", json={"name": "Jurte"}
        )
        assert material_set.status_code == 201
        set_id = material_set.get_json()["id"]

        _login(client, "mw")
        assert client.delete(f"/api/inventories/{inv_id}").status_code == 403

        blocked_type = client.delete(f"/api/material-types/{mt_used_id}")
        assert blocked_type.status_code == 409
        assert blocked_type.get_json()["error"] == "material_type_not_empty"

        assert client.delete(f"/api/pieces/{piece_id}").status_code == 204
        assert client.delete(f"/api/material-types/{mt_used_id}").status_code == 204
        assert client.delete(f"/api/material-types/{mt_empty_id}").status_code == 204
        assert client.delete(f"/api/sets/{set_id}").status_code == 204

        _login(client, "su")
        assert client.delete(f"/api/inventories/{inv_id}").status_code == 204
        assert client.get("/api/inventories").get_json() == []
    finally:
        tmp.cleanup()
