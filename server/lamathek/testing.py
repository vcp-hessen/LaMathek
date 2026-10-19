"""Test helpers shipped with the package (used when TESTING is set)."""

from flask.testing import FlaskClient


class ApiTestClient(FlaskClient):
    """Sends the CSRF header like the web client, so tests exercise real routes.

    A test that checks the guard itself removes it from ``environ_base``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environ_base["HTTP_X_REQUESTED_WITH"] = "lamathek"
