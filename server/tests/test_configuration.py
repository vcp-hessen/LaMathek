import os
import tempfile

from lamathek.app import create_app
from lamathek.config import Config
from lamathek.db import get_session
from lamathek.models.user import User
from lamathek.services.users import upsert_user_from_oidc


def test_settings_public_and_superuser_bootstrap():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.sqlite3")

        class TestConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            TESTING = True

        app = create_app(TestConfig)
        with app.app_context():
            from lamathek.db import Base, engine

            Base.metadata.create_all(engine)
            from lamathek.services.settings import get_installation_settings

            session = get_session()
            get_installation_settings(session)

        client = app.test_client()

        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "VCP Hessen"
        assert data["subtitle"] == "Landesmaterial"
        assert data["hostName"] == ""
        assert data["authProviderSameHost"] is False
        assert data["calendarBundesland"] == "HE"

        with app.app_context():
            session = get_session()
            user = upsert_user_from_oidc(
                session, sub="sub-1", name="First", email="a@example.com"
            )
            assert user.is_superuser is True

        with client.session_transaction() as sess:
            sess["user"] = {"sub": "sub-1", "name": "First", "email": "a@example.com"}

        me = client.get("/api/me")
        assert me.status_code == 200
        assert me.get_json()["isSuperuser"] is True

        patch = client.patch(
            "/api/settings",
            json={
                "title": "Neu",
                "subtitle": "Untertitel",
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
            },
        )
        assert patch.status_code == 200
        assert patch.get_json()["title"] == "Neu"
