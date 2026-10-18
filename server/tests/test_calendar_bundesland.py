from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

from conftest import app_with_db as _app_with_db, login as _login

_BASE_PATCH = {
    "title": "LaMathek",
    "subtitle": "Test",
    "legalName": "",
    "legalAddress": "",
    "email": "",
    "website": "",
    "phone": "",
    "representedBy": "",
    "register": "",
    "mapLatitude": 50.65,
    "mapLongitude": 9.16,
    "hostName": "",
    "hostAddress": "",
    "hostPrivacyUrl": "",
    "authProviderName": "",
    "authProviderSameHost": False,
    "authorityName": "",
    "authorityUrl": "",
}


def test_calendar_bundesland_patch_and_validation():
    app, tmp = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session, sub="su", name="SU", email=None, force_superuser=True
            )

        client = app.test_client()
        _login(client, "su")

        bad = client.patch("/api/settings", json={**_BASE_PATCH, "calendarBundesland": "XX"})
        assert bad.status_code == 400
        assert bad.get_json()["error"] == "invalid_calendar_bundesland"

        ok = client.patch("/api/settings", json={**_BASE_PATCH, "calendarBundesland": "BY"})
        assert ok.status_code == 200
        assert ok.get_json()["calendarBundesland"] == "BY"

        public = client.get("/api/settings")
        assert public.get_json()["calendarBundesland"] == "BY"
    finally:
        tmp.cleanup()
