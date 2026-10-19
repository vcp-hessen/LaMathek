import os
import tempfile

# Before any lamathek import: never read a developer's .env/.env.local (SMTP
# credentials, database path) during tests.
os.environ["LAMATHEK_SKIP_DOTENV"] = "1"
# Tests send mail synchronously via process_outbox_once, never from a thread.
os.environ["MAIL_OUTBOX_WORKER"] = "0"
for _name in [n for n in os.environ if n.startswith(("SMTP_", "AUTH_DEV_"))]:
    del os.environ[_name]

import pytest  # noqa: E402

from lamathek import db  # noqa: E402
from lamathek.app import create_app
from lamathek.config import Config
from lamathek.db import Base, get_session
from lamathek.services.settings import get_installation_settings


def app_with_db():
    """Return ``(app, tmp)``. Keep ``tmp`` alive until the test finishes."""
    tmp = tempfile.TemporaryDirectory()
    db_path = os.path.join(tmp.name, "test.sqlite3")

    class TestConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        TESTING = True

    app = create_app(TestConfig)
    with app.app_context():
        Base.metadata.create_all(db.engine)
        get_installation_settings(get_session())
    return app, tmp


def login(client, sub: str, *, email=None):
    with client.session_transaction() as sess:
        sess["user"] = {"sub": sub, "name": sub, "email": email}


@pytest.fixture(autouse=True)
def _loan_mail_sender_no_smtp():
    from lamathek.services.loan_notifications import set_mail_sender_for_tests

    def ok_sender(to, subject, text, html, cc, attachments=None):
        del to, subject, text, html, cc, attachments

    set_mail_sender_for_tests(ok_sender)
    yield
    set_mail_sender_for_tests(None)
