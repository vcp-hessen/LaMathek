from sqlalchemy import CheckConstraint, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lamathek.db import Base

DEFAULT_MAP_LATITUDE = 50.65
DEFAULT_MAP_LONGITUDE = 9.16


class InstallationSettings(Base):
    __tablename__ = "installation_settings"
    __table_args__ = (CheckConstraint("id = 1", name="installation_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(512), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    legal_address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    website: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    represented_by: Mapped[str] = mapped_column(Text, nullable=False, default="")
    register: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    map_latitude: Mapped[float] = mapped_column(
        Float, nullable=False, default=DEFAULT_MAP_LATITUDE
    )
    map_longitude: Mapped[float] = mapped_column(
        Float, nullable=False, default=DEFAULT_MAP_LONGITUDE
    )
