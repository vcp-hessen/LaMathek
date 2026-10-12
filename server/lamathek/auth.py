import logging

from authlib.integrations.flask_client import OAuth
from flask import Flask, session

oauth = OAuth()
logger = logging.getLogger(__name__)


def init_auth(app) -> None:
    oauth.init_app(app)
    metadata_url = app.config["OIDC_SERVER_METADATA_URL"]
    if metadata_url:
        oauth.register(
            name="oidc",
            client_id=app.config["OIDC_CLIENT_ID"],
            client_secret=app.config["OIDC_CLIENT_SECRET"],
            server_metadata_url=metadata_url,
            client_kwargs={"scope": app.config["OIDC_SCOPES"]},
        )


def validate_dev_bypass_config(app: Flask) -> None:
    if not app.config["AUTH_DEV_BYPASS"]:
        return
    if not (app.config["DEBUG"] or app.config["AUTH_DEV_BYPASS_ALLOW"]):
        raise RuntimeError(
            "AUTH_DEV_BYPASS is set but neither FLASK_DEBUG nor "
            "AUTH_DEV_BYPASS_ALLOW is enabled. Refusing to start."
        )
    sub = app.config["AUTH_DEV_SUB"].strip()
    if not sub:
        raise RuntimeError("AUTH_DEV_BYPASS is set but AUTH_DEV_SUB is missing.")
    logger.warning(
        "AUTH_DEV_BYPASS is active for sub=%s. OpenID Connect is not used for /login.",
        sub,
    )


def dev_bypass_enabled(app: Flask) -> bool:
    return bool(app.config["AUTH_DEV_BYPASS"])


def dev_bypass_identity(app: Flask) -> dict:
    return {
        "sub": app.config["AUTH_DEV_SUB"].strip(),
        "name": app.config["AUTH_DEV_NAME"].strip() or None,
        "email": app.config["AUTH_DEV_EMAIL"].strip() or None,
        "force_superuser": app.config["AUTH_DEV_SUPERUSER"],
    }


def oidc_configured(app) -> bool:
    return bool(
        app.config["OIDC_CLIENT_ID"]
        and app.config["OIDC_CLIENT_SECRET"]
        and app.config["OIDC_SERVER_METADATA_URL"]
    )


def current_user() -> dict | None:
    return session.get("user")


def session_actor_sub() -> str | None:
    user = session.get("user")
    if not user:
        return None
    sub = user.get("sub")
    return sub if sub else None


def session_impersonation() -> dict | None:
    return session.get("impersonation")


def effective_oidc_sub() -> str | None:
    imp = session_impersonation()
    if imp is not None:
        sub = imp.get("sub")
        if sub:
            return sub
    return session_actor_sub()
