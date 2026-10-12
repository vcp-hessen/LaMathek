from sqlalchemy import select

from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.services.inventories import create_inventory, grant_inventory_permission
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def test_active_inventory_readable_without_permission():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            upsert_user_from_oidc(
                session,
                sub="viewer",
                name="Viewer",
                email=None,
                force_superuser=False,
            )
            active = create_inventory(
                session, "Public Lager", visibility="active", notes="Abholung hinten"
            )
            internal = create_inventory(session, "Secret Lager", visibility="internal")
            session.commit()
            active_id = active.id
            internal_id = internal.id

        client = app.test_client()
        _login(client, "viewer")

        listed = client.get("/api/inventories")
        assert listed.status_code == 200
        rows = listed.get_json()
        assert [r["name"] for r in rows] == ["Public Lager"]
        assert rows[0]["canManage"] is False
        assert rows[0]["visibility"] == "active"
        assert rows[0]["notes"] == "Abholung hinten"

        detail = client.get(f"/api/inventories/{active_id}")
        assert detail.status_code == 200
        assert detail.get_json()["canManage"] is False

        assert client.get(f"/api/inventories/{internal_id}").status_code == 403

        types = client.get(f"/api/inventories/{active_id}/material-types")
        assert types.status_code == 200

        sets = client.get(f"/api/inventories/{active_id}/sets")
        assert sets.status_code == 200

        assert client.get(f"/api/inventories/{active_id}/loans").status_code == 403
        assert client.get(f"/api/inventories/{active_id}/permissions").status_code == 403

        denied_write = client.post(
            f"/api/inventories/{active_id}/material-types",
            json={"name": "X", "tracking": "piece", "variants": []},
        )
        assert denied_write.status_code == 403
    finally:
        tmp.cleanup()


def test_archived_inventory_hidden_from_viewers():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="viewer",
                name="Viewer",
                email=None,
                force_superuser=False,
            )
            archived = create_inventory(session, "Old Lager", visibility="archived")
            session.commit()
            archived_id = archived.id

        client = app.test_client()
        _login(client, "viewer")
        assert client.get("/api/inventories").get_json() == []
        assert client.get(f"/api/inventories/{archived_id}").status_code == 403
    finally:
        tmp.cleanup()


def test_manager_sets_visibility():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="mw",
                name="MW",
                email=None,
                force_superuser=False,
            )
            inv = create_inventory(session, "Lager")
            mw = session.scalar(select(User).where(User.oidc_sub == "mw"))
            grant_inventory_permission(session, mw, inv)
            session.commit()
            inv_id = inv.id

        client = app.test_client()
        _login(client, "mw")
        updated = client.patch(
            f"/api/inventories/{inv_id}",
            json={"name": "Lager", "visibility": "active"},
        )
        assert updated.status_code == 200
        assert updated.get_json()["visibility"] == "active"
        assert updated.get_json()["canManage"] is True

        bad = client.patch(
            f"/api/inventories/{inv_id}",
            json={"name": "Lager", "visibility": "nope"},
        )
        assert bad.status_code == 400
        assert bad.get_json()["error"] == "invalid_visibility"
    finally:
        tmp.cleanup()
