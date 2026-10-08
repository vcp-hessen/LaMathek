from flask import Blueprint, current_app, redirect, session

from lamathek.auth import (
    dev_bypass_enabled,
    dev_bypass_identity,
    oauth,
    oidc_configured,
)
from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc

auth_bp = Blueprint("auth", __name__)


def _start_session(
    sub: str,
    name: str | None,
    email: str | None,
    *,
    force_superuser: bool | None,
) -> None:
    db = get_session()
    upsert_user_from_oidc(
        db,
        sub=sub,
        name=name,
        email=email,
        force_superuser=force_superuser,
    )
    session["user"] = {"sub": sub, "name": name, "email": email}


@auth_bp.get("/login")
def login():
    if dev_bypass_enabled(current_app):
        identity = dev_bypass_identity(current_app)
        _start_session(
            identity["sub"],
            identity["name"],
            identity["email"],
            force_superuser=identity["force_superuser"],
        )
        return redirect(current_app.config["FRONTEND_URL"])

    if not oidc_configured(current_app):
        return (
            "OIDC is not configured. Set OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, and "
            "OIDC_SERVER_METADATA_URL, or enable AUTH_DEV_BYPASS for local development.",
            503,
        )
    redirect_uri = current_app.config["OIDC_REDIRECT_URI"]
    return oauth.oidc.authorize_redirect(redirect_uri)


@auth_bp.get("/auth/callback")
def auth_callback():
    if not oidc_configured(current_app):
        return "OIDC is not configured.", 503
    token = oauth.oidc.authorize_access_token()
    userinfo = token.get("userinfo")
    if userinfo is None:
        userinfo = oauth.oidc.userinfo()
    sub = userinfo.get("sub")
    if not sub:
        return "OpenID Connect userinfo missing sub.", 400
    name = userinfo.get("name") or userinfo.get("preferred_username")
    email = userinfo.get("email")
    db = get_session()
    upsert_user_from_oidc(db, sub=sub, name=name, email=email)
    session["user"] = {"sub": sub, "name": name, "email": email}
    return redirect(current_app.config["FRONTEND_URL"])


@auth_bp.post("/logout")
def logout():
    session.pop("user", None)
    return "", 204
