from sqlalchemy import select
from sqlalchemy.orm import Session

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
    session: Session, *, title: str, subtitle: str
) -> InstallationSettings:
    settings = get_installation_settings(session)
    settings.title = title.strip()
    settings.subtitle = subtitle.strip()
    session.commit()
    session.refresh(settings)
    return settings
