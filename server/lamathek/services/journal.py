"""Append-only Verleih journal."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lamathek.models.journal import LoanJournalEntry
from lamathek.models.loan import LoanLine
from lamathek.models.user import User


def _real_actor_id(actor: User | None) -> int | None:
    """Superuser impersonating ``actor`` in this request (set by require_login)."""
    from flask import g, has_request_context

    if actor is None or not has_request_context():
        return None
    real = getattr(g, "real_actor", None)
    if real is None or real.id == actor.id:
        return None
    return real.id


def append_journal(
    session: Session,
    kind: str,
    actor: User | None,
    payload: dict[str, Any],
    *,
    loan_id: int | None = None,
    piece_id: int | None = None,
    loan_line_id: int | None = None,
) -> LoanJournalEntry:
    if loan_id is None and loan_line_id is not None:
        line = session.get(LoanLine, loan_line_id)
        if line is not None:
            loan_id = line.loan_id
            if piece_id is None:
                piece_id = line.piece_id
    if loan_id is None and piece_id is None and loan_line_id is None:
        raise ValueError("journal_target_required")
    entry = LoanJournalEntry(
        kind=kind,
        real_actor_user_id=_real_actor_id(actor),
        payload=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        loan_id=loan_id,
        piece_id=piece_id,
        loan_line_id=loan_line_id,
        actor_user_id=actor.id if actor is not None else None,
    )
    session.add(entry)
    return entry


def journal_line_action(
    session: Session,
    *,
    actor: User | None,
    loan_id: int,
    line: LoanLine,
    action: str,
    **extra: Any,
) -> None:
    payload: dict[str, Any] = {"action": action, "status": line.status, **extra}
    append_journal(
        session,
        f"line.{action}",
        actor,
        payload,
        loan_id=loan_id,
        piece_id=line.piece_id,
        loan_line_id=line.id,
    )


def list_loan_journal(session: Session, loan_id: int) -> list[LoanJournalEntry]:
    return list(
        session.scalars(
            select(LoanJournalEntry)
            .where(LoanJournalEntry.loan_id == loan_id)
            .options(
                selectinload(LoanJournalEntry.actor_user),
                selectinload(LoanJournalEntry.real_actor_user),
            )
            .order_by(LoanJournalEntry.created_at.desc(), LoanJournalEntry.id.desc())
        ).all()
    )


def list_piece_journal(session: Session, piece_id: int) -> list[LoanJournalEntry]:
    from sqlalchemy import or_

    line_ids = list(
        session.scalars(select(LoanLine.id).where(LoanLine.piece_id == piece_id)).all()
    )
    clauses = [LoanJournalEntry.piece_id == piece_id]
    if line_ids:
        clauses.append(LoanJournalEntry.loan_line_id.in_(line_ids))
    return list(
        session.scalars(
            select(LoanJournalEntry)
            .where(or_(*clauses))
            .options(
                selectinload(LoanJournalEntry.actor_user),
                selectinload(LoanJournalEntry.real_actor_user),
            )
            .order_by(LoanJournalEntry.created_at.desc(), LoanJournalEntry.id.desc())
        ).all()
    )
