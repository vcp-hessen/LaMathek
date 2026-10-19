"""Test helpers shipped with the package (used when TESTING is set)."""

from flask.testing import FlaskClient


class ApiTestClient(FlaskClient):
    """Behaves like the web client plus the background mail worker.

    Sends the CSRF header (a test of the guard removes it from ``environ_base``)
    and, after every request, delivers due outbox mails synchronously — as the
    worker would right after the commit — so tests see sent mails deterministically.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environ_base["HTTP_X_REQUESTED_WITH"] = "lamathek"

    def open(self, *args, **kwargs):
        response = super().open(*args, **kwargs)
        if self.application.config.get("OUTBOX_DRAIN_IN_TESTS", True):
            from lamathek import db
            from lamathek.services.outbox import process_outbox_once

            with self.application.app_context():
                session = db.SessionLocal()
                try:
                    process_outbox_once(session)
                finally:
                    session.close()
        return response
