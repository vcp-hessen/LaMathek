from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from lamathek.db import Base

CALENDAR_SCOPE_USER = "user"
CALENDAR_SCOPE_INVENTORY = "inventory"


class CalendarFeed(Base):
    __tablename__ = "calendar_feeds"
    __table_args__ = (
        UniqueConstraint("user_id", "scope", "inventory_id", name="uq_calendar_feed_scope"),
        UniqueConstraint("token_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    scope: Mapped[str] = mapped_column(String(16))
    inventory_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
