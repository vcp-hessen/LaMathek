import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from lamathek.app import create_app
from lamathek.config import Config
from lamathek.db import get_session
from lamathek.services.mail import send_mail
from lamathek.services.outbox import process_outbox_once
from lamathek.services.mail_templates import render_mail
from lamathek.services.settings import update_installation_settings
from lamathek.services.users import upsert_user_from_oidc


def _app_with_smtp(**smtp_overrides):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.sqlite3")

        class TestConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            TESTING = True
            SMTP_HOST = "smtp.example.test"
            SMTP_FROM = "noreply@lamathek.test"
            SMTP_PORT = 587
            SMTP_USERNAME = ""
            SMTP_PASSWORD = ""
            SMTP_STARTTLS = True
            SMTP_SSL = False

        for key, value in smtp_overrides.items():
            setattr(TestConfig, key, value)

        app = create_app(TestConfig)
        with app.app_context():
            from lamathek.db import Base, engine

            Base.metadata.create_all(engine)

        yield app, TestConfig


@pytest.fixture(autouse=True)
def _real_sender():
    """These tests exercise send_mail itself (SMTP is patched)."""
    from lamathek.services.loan_notifications import set_mail_sender_for_tests

    set_mail_sender_for_tests(None)
    yield


def _drain(app) -> None:
    with app.app_context():
        process_outbox_once(get_session())


def _login_superuser(client, app, sub: str = "mail-su"):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session,
            sub=sub,
            name="Super",
            email="super@example.com",
            force_superuser=True,
        )
    with client.session_transaction() as sess:
        sess["user"] = {"sub": sub, "name": "Super", "email": "super@example.com"}


def test_mail_status_requires_superuser():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        client = app.test_client()
        response = client.get("/api/mail/status")
        assert response.status_code == 401
    finally:
        gen.close()


def test_mail_test_flow_success():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        client = app.test_client()
        _login_superuser(client, app)

        status = client.get("/api/mail/status")
        assert status.status_code == 200
        data = status.get_json()
        assert data["configured"] is True
        assert data["host"] == "smtp.example.test"
        assert data["fromAddress"] == "noreply@lamathek.test"

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("lamathek.services.mail.smtplib.SMTP", return_value=mock_smtp):
            start = client.post(
                "/api/mail/test",
                json={"to": "recipient@example.com"},
            )
            assert start.status_code == 202
            job_id = start.get_json()["id"]
            poll = client.get(f"/api/mail/test/{job_id}")
            assert poll.status_code == 200
            final = poll.get_json()
            assert final["status"] == "sent"
            mock_smtp.starttls.assert_called_once()
            mock_smtp.send_message.assert_called_once()
            sent = mock_smtp.send_message.call_args[0][0]
            html_parts = [
                part
                for part in sent.walk()
                if part.get_content_type() == "text/html"
            ]
            assert len(html_parts) == 1
            assert "#004287" in html_parts[0].get_content()

        other = client.get(f"/api/mail/test/{job_id}")
        assert other.status_code == 200
    finally:
        gen.close()


def test_mail_test_not_configured():
    gen = _app_with_smtp(SMTP_HOST="")
    app, _ = next(gen)
    try:
        client = app.test_client()
        _login_superuser(client, app)

        status = client.get("/api/mail/status")
        assert status.get_json()["configured"] is False

        response = client.post("/api/mail/test", json={"to": "a@example.com"})
        assert response.status_code == 400
        assert response.get_json()["error"] == "smtp_not_configured"
    finally:
        gen.close()


def test_mail_test_smtp_failure_detail():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        client = app.test_client()
        _login_superuser(client, app)

        import smtplib

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp.send_message.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )

        with patch("lamathek.services.mail.smtplib.SMTP", return_value=mock_smtp):
            start = client.post("/api/mail/test", json={"to": "a@example.com"})
            job_id = start.get_json()["id"]
            _drain(app)
            final = client.get(f"/api/mail/test/{job_id}").get_json()
            # A test mail gets one attempt, so the error shows at once.
            assert final["status"] == "failed"
            assert "Authentication" in final["detail"]
    finally:
        gen.close()


def test_mail_test_job_not_visible_to_other_user():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        client = app.test_client()
        _login_superuser(client, app, sub="owner")

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("lamathek.services.mail.smtplib.SMTP", return_value=mock_smtp):
            start = client.post("/api/mail/test", json={"to": "a@example.com"})
            job_id = start.get_json()["id"]

        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="other",
                name="Other",
                email="other@example.com",
                force_superuser=True,
            )

        with client.session_transaction() as sess:
            sess["user"] = {
                "sub": "other",
                "name": "Other",
                "email": "other@example.com",
            }

        response = client.get(f"/api/mail/test/{job_id}")
        assert response.status_code == 404
    finally:
        gen.close()


def test_render_mail_includes_installation_and_vcp_styles():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        with app.app_context():
            session = get_session()
            update_installation_settings(
                session,
                title="VCP Hessen",
                subtitle="Landesmaterial",
                legal_name="VCP Landesverband",
                legal_address="Musterstraße 1\n12345 Ort",
                email="info@example.org",
                website="",
                phone="",
                represented_by="",
                register="",
                map_latitude=50.65,
                map_longitude=9.16,
                host_name="",
                host_address="",
                host_privacy_url="",
                auth_provider_name="",
                auth_provider_same_host=False,
                authority_name="",
                authority_url="",
            )
            subject, text, html = render_mail(
                "test",
                heading="Hallo",
                paragraphs=["Ein Absatz."],
            )
        assert subject == "[VCP Hessen] Testmail"
        assert "Hallo" in text
        assert "Ein Absatz." in text
        assert "#004287" in html
        assert "#fecf16" in html
        assert "data:image/png;base64," in html
        assert "VCP Hessen" in html
        assert "Hallo" in html
        assert "/impressum" in html
        assert "Datenschutz" in html
        assert "VCP Landesverband · Musterstraße 1, 12345 Ort" in html
        assert "VCP Landesverband · Musterstraße 1, 12345 Ort" in text
    finally:
        gen.close()


def test_send_mail_from_uses_installation_title_when_only_address():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with app.app_context():
            with patch("lamathek.services.mail.smtplib.SMTP", return_value=mock_smtp):
                send_mail("to@example.com", "Subject", "Plain")

        sent = mock_smtp.send_message.call_args[0][0]
        assert sent["From"] == "VCP Hessen <noreply@lamathek.test>"
    finally:
        gen.close()


def test_send_mail_multipart():
    gen = _app_with_smtp()
    app, _ = next(gen)
    try:
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with app.app_context():
            with patch("lamathek.services.mail.smtplib.SMTP", return_value=mock_smtp):
                send_mail(
                    "to@example.com",
                    "Subject",
                    "Plain",
                    html="<p>HTML</p>",
                )

        sent = mock_smtp.send_message.call_args[0][0]
        types = {part.get_content_type() for part in sent.walk()}
        assert "text/plain" in types
        assert "text/html" in types
    finally:
        gen.close()
