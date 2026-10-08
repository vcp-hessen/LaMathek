from lamathek.models.inventory import Inventory
from lamathek.models.settings import InstallationSettings
from lamathek.models.user import User


def user_to_json(user: User) -> dict:
    return {
        "id": user.id,
        "sub": user.oidc_sub,
        "name": user.name,
        "email": user.email,
        "isSuperuser": user.is_superuser,
        "role": user.role,
    }


def inventory_to_json(inventory: Inventory) -> dict:
    return {
        "id": inventory.id,
        "name": inventory.name,
    }


def settings_to_json(settings: InstallationSettings) -> dict:
    return {
        "title": settings.title,
        "subtitle": settings.subtitle,
    }
