from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lamathek.db import Base


class LoanJournalEntry(Base):
    __tablename__ = "loan_journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Superuser behind an impersonated action; actor_user_id is the impersonated user.
    real_actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text(), default="{}", server_default="{}")
    loan_id: Mapped[int | None] = mapped_column(
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=True,
    )
    piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("pieces.id", ondelete="SET NULL"),
        nullable=True,
    )
    loan_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_lines.id", ondelete="SET NULL"),
        nullable=True,
    )

    actor_user: Mapped["User | None"] = relationship(foreign_keys=[actor_user_id])
    real_actor_user: Mapped["User | None"] = relationship(foreign_keys=[real_actor_user_id])
    loan: Mapped["Loan"] = relationship()
    piece: Mapped["Piece | None"] = relationship()
    loan_line: Mapped["LoanLine | None"] = relationship()
