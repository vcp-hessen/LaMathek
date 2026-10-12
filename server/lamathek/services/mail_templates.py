import base64
from pathlib import Path

from flask import current_app, has_app_context

from lamathek.config import Config, checkout_root
from lamathek.db import get_session
from lamathek.services.settings import get_installation_settings


def _cfg(name: str, default=None):
    if has_app_context():
        return current_app.config.get(name, default)
    return getattr(Config, name, default)


def _single_line(raw: str) -> str:
    parts = [part.strip() for part in raw.replace("\r", "\n").split("\n") if part.strip()]
    return ", ".join(parts)


def _join_parts(*parts: str) -> str:
    return " · ".join(part for part in parts if part)


def _website_href(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed:
        return ""
    if trimmed.lower().startswith(("http://", "https://")):
        return trimmed
    return f"https://{trimmed}"


def mail_logo_src() -> str:
    """Inline PNG (same as web/public/app-icon.png) for mail clients without SVG."""
    root = checkout_root()
    for rel in ("web/dist/app-icon.png", "web/public/app-icon.png"):
        path = root / rel
        if path.is_file():
            encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    packaged = (
        Path(__file__).resolve().parent.parent / "templates" / "mail" / "app-icon.png"
    )
    if packaged.is_file():
        encoded = base64.standard_b64encode(packaged.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    return ""


def mail_base_context() -> dict:
    session = get_session()
    settings = get_installation_settings(session)
    frontend_url = str(_cfg("FRONTEND_URL", "") or "").strip().rstrip("/")
    legal_name = (settings.legal_name or "").strip()
    title = (settings.title or "").strip()
    website_raw = (settings.website or "").strip()
    website_href = _website_href(website_raw)
    provider_label = legal_name or title
    impressum_url = f"{frontend_url}/impressum" if frontend_url else ""
    privacy_url = f"{frontend_url}/datenschutz" if frontend_url else ""
    legal_address = _single_line(settings.legal_address or "")
    contact_email = (settings.email or "").strip()
    phone = (settings.phone or "").strip()
    represented_by = _single_line(settings.represented_by or "")
    register = _single_line(settings.register or "")
    footer_identity = _join_parts(legal_name, legal_address)
    footer_meta = _join_parts(represented_by, register)
    return {
        "installation_title": settings.title,
        "installation_subtitle": settings.subtitle,
        "frontend_url": frontend_url,
        "logo_src": mail_logo_src(),
        "provider_label": provider_label,
        "website_raw": website_raw,
        "website_href": website_href,
        "impressum_url": impressum_url,
        "privacy_url": privacy_url,
        "legal_name": legal_name,
        "legal_address": legal_address,
        "contact_email": contact_email,
        "phone": phone,
        "represented_by": represented_by,
        "register": register,
        "footer_identity": footer_identity,
        "footer_meta": footer_meta,
    }


def format_mail_subject(raw_subject: str, installation_title: str) -> str:
    subject = raw_subject.strip()
    title = installation_title.strip()
    if not title:
        return subject
    prefix = f"[{title}] "
    if subject.startswith(prefix) or subject.startswith(f"[{title}]"):
        return subject
    return f"{prefix}{subject}"


def render_mail(template: str, **context) -> tuple[str, str, str]:
    """Return (subject, plain text, html) for a mail template name without extension."""
    variables = {**mail_base_context(), **context}
    env = current_app.jinja_env
    raw_subject = (
        env.get_template(f"mail/{template}.subject.txt").render(variables).strip()
    )
    subject = format_mail_subject(raw_subject, str(variables.get("installation_title", "")))
    text = env.get_template(f"mail/{template}.txt").render(variables)
    html = env.get_template(f"mail/{template}.html").render(variables)
    return subject, text, html
