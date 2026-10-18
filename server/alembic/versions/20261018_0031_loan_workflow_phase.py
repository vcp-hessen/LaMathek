"""loan phase as workflow step

Revision ID: 20261018_0031
Revises: 20261018_0030
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, selectinload

revision = "20261018_0031"
down_revision = "20261018_0030"
branch_labels = None
depends_on = None

_CK_LOAN_PHASE = "ck_loan_phase"
_NEW_PHASE_CHECK = (
    "phase IN ('draft', 'review', 'pack', 'handover', 'return', 'restock', 'closed')"
)
_OLD_PHASE_CHECK = "phase IN ('draft', 'active', 'closed')"


def _column_exists(table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def _check_constraint_exists(table: str, name: str) -> bool:
    insp = inspect(op.get_bind())
    return name in {c["name"] for c in insp.get_check_constraints(table)}


def _drop_phase_check_if_present() -> None:
    if not _check_constraint_exists("loans", _CK_LOAN_PHASE):
        return
    with op.batch_alter_table("loans") as batch_op:
        batch_op.drop_constraint(_CK_LOAN_PHASE, type_="check")


def _create_phase_check(sqltext: str) -> None:
    if _check_constraint_exists("loans", _CK_LOAN_PHASE):
        return
    with op.batch_alter_table("loans") as batch_op:
        batch_op.create_check_constraint(_CK_LOAN_PHASE, sqltext)


def _open_step_from_lines(lines) -> str | None:
    from lamathek.models.loan import LINE_STATUSES_TERMINAL

    open_statuses = {
        line.status for line in lines if line.status not in LINE_STATUSES_TERMINAL
    }
    if not open_statuses:
        return None
    if "requested" in open_statuses:
        return "review"
    if "confirmed" in open_statuses:
        return "pack"
    if "packed" in open_statuses:
        return "handover"
    if "picked_up" in open_statuses:
        return "return"
    if "return_reported" in open_statuses:
        return "restock"
    return None


def _all_terminal(lines) -> bool:
    from lamathek.models.loan import LINE_STATUSES_TERMINAL

    if not lines:
        return True
    return all(line.status in LINE_STATUSES_TERMINAL for line in lines)


def upgrade() -> None:
    # ck_loan_phase is on the SQLAlchemy model (create_all in tests) but was never
    # added in Alembic; only drop when present.
    _drop_phase_check_if_present()

    bind = op.get_bind()
    session = Session(bind=bind)
    from lamathek.models.loan import Loan

    loans = session.scalars(
        select(Loan).options(selectinload(Loan.lines))
    ).all()
    for loan in loans:
        if loan.phase == "closed":
            continue
        if loan.phase == "draft":
            continue
        if loan.phase != "active":
            continue
        pending = (getattr(loan, "pending_mail_step", None) or "").strip()
        if pending:
            loan.phase = pending
        elif _all_terminal(loan.lines):
            loan.phase = "closed"
        else:
            loan.phase = _open_step_from_lines(loan.lines) or "review"
    session.commit()

    if _column_exists("loans", "pending_mail_step"):
        op.drop_column("loans", "pending_mail_step")

    _create_phase_check(_NEW_PHASE_CHECK)


def downgrade() -> None:
    if not _column_exists("loans", "pending_mail_step"):
        op.add_column(
            "loans",
            sa.Column("pending_mail_step", sa.String(length=16), nullable=True),
        )

    _drop_phase_check_if_present()

    bind = op.get_bind()
    session = Session(bind=bind)
    from lamathek.models.loan import Loan

    loans = session.scalars(select(Loan)).all()
    for loan in loans:
        if loan.phase in ("draft", "closed"):
            continue
        loan.pending_mail_step = loan.phase
        loan.phase = "active"
    session.commit()

    _create_phase_check(_OLD_PHASE_CHECK)
