from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from lamathek.db import Base


class InstallationSettings(Base):
    __tablename__ = "installation_settings"
    __table_args__ = (CheckConstraint("id = 1", name="installation_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(512), nullable=False)
