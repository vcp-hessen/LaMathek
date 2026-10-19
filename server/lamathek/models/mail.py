from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from lamathek.db import Base

OUTBOX_PENDING = "pending"
OUTBOX_SENDING = "sending"
OUTBOX_SENT = "sent"
OUTBOX_FAILED = "failed"

OUTBOX_KIND_LOAN = "loan"
OUTBOX_KIND_TEST = "test"


class MailOutbox(Base):
    """A mail waiting to be sent (or already sent / given up), written in the same
    transaction as the change it reports. A background worker delivers it."""

    __tablename__ = "mail_outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    loan_id: Mapped[int | None] = mapped_column(
        ForeignKey("loans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    audience: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    to_address: Mapped[str] = mapped_column(String(320))
    cc: Mapped[list[str]] = mapped_column(JSON, default=list)
    subject: Mapped[str] = mapped_column(Text())
    text_body: Mapped[str] = mapped_column(Text())
    html_body: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # Rendered at send time from the loan's then current state.
    pdf_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=OUTBOX_PENDING, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=6)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text(), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
