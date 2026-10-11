import os
import tempfile

from lamathek import db
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
