from sqlalchemy.orm import Session

from lamathek.bundesland import DEFAULT_CALENDAR_BUNDESLAND
from lamathek.models.settings import InstallationSettings

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
    host_name: str,
    host_address: str,
    host_privacy_url: str,
    auth_provider_name: str,
    auth_provider_same_host: bool,
    authority_name: str,
    authority_url: str,
    calendar_bundesland: str = DEFAULT_CALENDAR_BUNDESLAND,
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
    settings.host_name = host_name.strip()
    settings.host_address = host_address.strip()
    settings.host_privacy_url = host_privacy_url.strip()
    settings.auth_provider_name = auth_provider_name.strip()
    settings.auth_provider_same_host = auth_provider_same_host
    settings.authority_name = authority_name.strip()
    settings.authority_url = authority_url.strip()
    settings.calendar_bundesland = calendar_bundesland
    session.commit()
    session.refresh(settings)
    return settings
