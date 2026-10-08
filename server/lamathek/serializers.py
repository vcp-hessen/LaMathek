from lamathek.models.settings import InstallationSettings
from lamathek.models.user import User


def user_to_json(user: User) -> dict:
    return {
        "id": user.id,
        "sub": user.oidc_sub,
        "name": user.name,
        "email": user.email,
        "isSuperuser": user.is_superuser,
    }


def settings_to_json(settings: InstallationSettings) -> dict:
    return {
        "title": settings.title,
        "subtitle": settings.subtitle,
    }
