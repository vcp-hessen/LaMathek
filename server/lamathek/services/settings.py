from sqlalchemy import select
from sqlalchemy.orm import Session

from lamathek.models.settings import (
    DEFAULT_MAP_LATITUDE,
    DEFAULT_MAP_LONGITUDE,
    InstallationSettings,
)

DEFAULT_TITLE = "VCP Hessen"
DEFAULT_SUBTITLE = "Landesmaterial"


def get_installation_settings(session: Session) -> InstallationSettings:
    settings = session.get(InstallationSettings, 1)
    if settings is None:
        settings = InstallationSettings(
            id=1, title=DEFAULT_TITLE, subtitle=DEFAULT_SUBTITLE
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def update_installation_settings(
    session: Session,
    *,
    title: str,
    subtitle: str,
    legal_name: str,
    legal_address: str,
    email: str,
    website: str,
    phone: str,
    represented_by: str,
    register: str,
    map_latitude: float,
    map_longitude: float,
) -> InstallationSettings:
    settings = get_installation_settings(session)
    settings.title = title.strip()
    settings.subtitle = subtitle.strip()
    settings.legal_name = legal_name.strip()
    settings.legal_address = legal_address.strip()
    settings.email = email.strip()
    settings.website = website.strip()
    settings.phone = phone.strip()
    settings.represented_by = represented_by.strip()
    settings.register = register.strip()
    settings.map_latitude = map_latitude
    settings.map_longitude = map_longitude
    session.commit()
    session.refresh(settings)
    return settings


def default_map_center() -> tuple[float, float]:
    return (DEFAULT_MAP_LATITUDE, DEFAULT_MAP_LONGITUDE)
