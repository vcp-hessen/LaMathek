from unittest.mock import patch

from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login


def test_inventory_location_fields_round_trip():
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

        client = app.test_client()
        _login(client, "su")
        created = client.post(
            "/api/inventories",
            json={
                "name": "Donnerskopf",
                "address": "Donnerskopf 1\n61273 Wehrheim",
                "latitude": 50.205,
                "longitude": 8.542,
                "notes": "Schlüssel beim Hausmeister",
            },
        )
        assert created.status_code == 201
        data = created.get_json()
        assert data["address"].startswith("Donnerskopf")
        assert data["latitude"] == 50.205
        assert data["notes"] == "Schlüssel beim Hausmeister"

        inv_id = data["id"]
        cleared = client.patch(
            f"/api/inventories/{inv_id}",
            json={
                "name": "Donnerskopf",
                "address": None,
                "latitude": None,
                "longitude": None,
                "notes": None,
            },
        )
        assert cleared.status_code == 200
        assert cleared.get_json()["latitude"] is None
    finally:
        tmp.cleanup()


def test_geocode_endpoint():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            mw = upsert_user_from_oidc(
                session,
                sub="mw",
                name="MW",
                email=None,
                force_superuser=False,
            )
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        _login(client, "mw")
        assert client.get("/api/geocode", query_string={"q": "Wiesbaden"}).status_code == 403

        _login(client, "su")
        with patch(
            "lamathek.routes.geocode_routes.geocode_address",
            return_value=(50.0826, 8.2400),
        ):
            ok = client.get("/api/geocode", query_string={"q": "Wiesbaden"})
        assert ok.status_code == 200
        assert ok.get_json() == {"latitude": 50.0826, "longitude": 8.24}

        with patch(
            "lamathek.routes.geocode_routes.geocode_address",
            side_effect=__import__(
                "lamathek.services.geocoding", fromlist=["GeocodingError"]
            ).GeocodingError("not_found"),
        ):
            missing = client.get("/api/geocode", query_string={"q": "xyz"})
        assert missing.status_code == 404
    finally:
        tmp.cleanup()


def test_settings_impressum_and_map_center():
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

        client = app.test_client()
        public = client.get("/api/settings")
        assert public.status_code == 200
        assert "mapLatitude" in public.get_json()

        _login(client, "su")
        patch = client.patch(
            "/api/settings",
            json={
                "title": "LaMathek",
                "subtitle": "Test",
                "legalName": "VCP Hessen e. V.",
                "legalAddress": "Musterstraße 1",
                "email": "info@example.org",
                "website": "https://vcp-hessen.de",
                "phone": "",
                "representedBy": "Vorstand",
                "register": "VR 123",
                "mapLatitude": 50.1,
                "mapLongitude": 8.2,
                "hostName": "Hetzner Online GmbH",
                "hostAddress": "Industriestr. 25\n91710 Gunzenhausen",
                "hostPrivacyUrl": "https://www.hetzner.com/de/legal/privacy-policy",
                "authProviderName": "Keycloak der VCP-Hessen-Landescloud",
                "authProviderSameHost": True,
                "authorityName": "Hessischer Beauftragter für Datenschutz und Informationsfreiheit",
                "authorityUrl": "https://datenschutz.hessen.de",
            },
        )
        assert patch.status_code == 200
        body = patch.get_json()
        assert body["legalName"] == "VCP Hessen e. V."
        assert body["website"] == "https://vcp-hessen.de"
        assert body["mapLatitude"] == 50.1
        assert body["hostName"] == "Hetzner Online GmbH"
        assert body["authProviderSameHost"] is True
        assert body["authorityName"].startswith("Hessischer")
    finally:
        tmp.cleanup()
