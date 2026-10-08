import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from lamathek.app import create_app
from lamathek.config import Config
from lamathek import db
from lamathek.db import Base, get_session
from lamathek.services.settings import get_installation_settings


class DevBypassConfig(Config):
    TESTING = True
    AUTH_DEV_BYPASS = True
    AUTH_DEV_BYPASS_ALLOW = True
    AUTH_DEV_SUB = "dev:test"
    AUTH_DEV_NAME = "Dev Tester"
    AUTH_DEV_EMAIL = "dev@test.example"
    AUTH_DEV_SUPERUSER = True
    OIDC_CLIENT_ID = "client"
    OIDC_CLIENT_SECRET = "secret"
    OIDC_SERVER_METADATA_URL = "https://idp.example/.well-known/openid-configuration"


@pytest.fixture()
def dev_app():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.sqlite3")

        class _Config(DevBypassConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

        app = create_app(_Config)
        with app.app_context():
            Base.metadata.create_all(db.engine)
            get_installation_settings(get_session())
        yield app


def test_dev_bypass_login_without_oidc_redirect(dev_app):
    client = dev_app.test_client()
    with patch(
        "lamathek.routes.auth_routes.oauth.oidc.authorize_redirect",
        MagicMock(),
    ) as redirect_mock:
        response = client.get("/login", follow_redirects=False)
        redirect_mock.assert_not_called()
    assert response.status_code == 302
    assert response.location == dev_app.config["FRONTEND_URL"]

    me = client.get("/api/me")
    assert me.status_code == 200
    body = me.get_json()
    assert body["sub"] == "dev:test"
    assert body["isSuperuser"] is True


def test_auth_mode_reports_dev_bypass(dev_app):
    client = dev_app.test_client()
    response = client.get("/api/auth/mode")
    assert response.status_code == 200
    assert response.get_json() == {"devBypass": True}


def test_dev_bypass_refused_without_guard():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.sqlite3")

        class _Config(DevBypassConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            AUTH_DEV_BYPASS_ALLOW = False
            DEBUG = False

        with pytest.raises(RuntimeError, match="AUTH_DEV_BYPASS"):
            create_app(_Config)
