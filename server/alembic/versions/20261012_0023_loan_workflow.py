"""loan workflow: per-line status, borrower, phase, pickup/return notes

Revision ID: 20261012_0023
Revises: 20261012_0022
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0023"
down_revision: Union[str, None] = "20261012_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LINE_DRAFT = "draft"
LINE_REQUESTED = "requested"
LINE_CONFIRMED = "confirmed"
LINE_PACKED = "packed"
LINE_PICKED_UP = "picked_up"
LINE_RETURN_REPORTED = "return_reported"
LINE_RESTOCKED = "restocked"
LINE_UNAVAILABLE = "unavailable"
LINE_NOT_PACKED = "not_packed"
LINE_NOT_PICKED_UP = "not_picked_up"
LINE_NOT_RETURNED = "not_returned"
LINE_WITHDRAWN = "withdrawn"

LOAN_PLANNED = "planned"
LOAN_HANDED_OUT = "handed_out"
LOAN_CLOSED = "closed"

PHASE_DRAFT = "draft"
PHASE_ACTIVE = "active"
PHASE_CLOSED = "closed"


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("phone", sa.String(length=64), nullable=False, server_default="")
        )

    with op.batch_alter_table("photos") as batch_op:
        batch_op.add_column(
            sa.Column("loan_photo_role", sa.String(length=16), nullable=True)
        )

    op.execute(
        sa.text("UPDATE photos SET loan_photo_role = 'loan' WHERE loan_id IS NOT NULL")
    )

    with op.batch_alter_table("loans") as batch_op:
        batch_op.add_column(
            sa.Column("phase", sa.String(length=16), nullable=False, server_default="draft")
        )
        batch_op.add_column(sa.Column("contact_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("pickup_note", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("return_note", sa.Text(), nullable=False, server_default=""))
        batch_op.create_foreign_key(
            "fk_loans_contact_user",
            "users",
            ["contact_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        sa.text(
            "UPDATE loans SET phase = :draft WHERE status = :planned"
        ).bindparams(draft=PHASE_DRAFT, planned=LOAN_PLANNED)
    )
    op.execute(
        sa.text(
            "UPDATE loans SET phase = :active WHERE status = :handed"
        ).bindparams(active=PHASE_ACTIVE, handed=LOAN_HANDED_OUT)
    )
    op.execute(
        sa.text("UPDATE loans SET phase = :phase WHERE status = :status").bindparams(
            phase=PHASE_CLOSED, status=LOAN_CLOSED
        )
    )

    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=24), nullable=False, server_default="draft")
        )
        batch_op.add_column(sa.Column("note", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("replaces_line_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_loan_lines_replaces",
            "loan_lines",
            ["replaces_line_id"],
            ["id"],
            ondelete="SET NULL",
        )

    conn = op.get_bind()
    loans = conn.execute(sa.text("SELECT id, status FROM loans")).fetchall()
    for loan_id, loan_status in loans:
        if loan_status == LOAN_PLANNED:
            line_status = LINE_DRAFT
        elif loan_status == LOAN_HANDED_OUT:
            line_status = LINE_PICKED_UP
        else:
            line_status = LINE_RESTOCKED
        conn.execute(
            sa.text("UPDATE loan_lines SET status = :st WHERE loan_id = :lid").bindparams(
                st=line_status, lid=loan_id
            )
        )

    if conn.dialect.name == "sqlite":
        return_rows = conn.execute(
            sa.text(
                """
                SELECT lrl.loan_line_id, lrl.outcome
                FROM loan_return_lines lrl
                JOIN loan_returns lr ON lr.id = lrl.loan_return_id
                JOIN loans l ON l.id = lr.loan_id
                WHERE l.status = :closed
                """
            ).bindparams(closed=LOAN_CLOSED)
        ).fetchall()
        for line_id, outcome in return_rows:
            st = LINE_RESTOCKED if outcome == "returned" else LINE_NOT_RETURNED
            conn.execute(
                sa.text("UPDATE loan_lines SET status = :st WHERE id = :lid").bindparams(
                    st=st, lid=line_id
                )
            )

        open_return = conn.execute(
            sa.text(
                """
                SELECT lrl.loan_line_id, lrl.outcome, ll.quantity
                FROM loan_return_lines lrl
                JOIN loan_returns lr ON lr.id = lrl.loan_return_id
                JOIN loans l ON l.id = lr.loan_id
                JOIN loan_lines ll ON ll.id = lrl.loan_line_id
                WHERE l.status = :handed
                """
            ).bindparams(handed=LOAN_HANDED_OUT)
        ).fetchall()
        for line_id, outcome, _qty in open_return:
            if outcome == "returned":
                conn.execute(
                    sa.text(
                        "UPDATE loan_lines SET status = :st WHERE id = :lid"
                    ).bindparams(st=LINE_RETURN_REPORTED, lid=line_id)
                )

    with op.batch_alter_table("loans") as batch_op:
        batch_op.alter_column("responsible_user_id", new_column_name="borrower_user_id")
        batch_op.alter_column("starts_on", new_column_name="pickup_on")
        batch_op.alter_column("ends_on", new_column_name="return_on")
        batch_op.drop_column("status")

    op.drop_table("loan_return_lines")
    op.drop_table("loan_returns")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.create_index(
            "uq_loan_draft_per_borrower",
            "loans",
            ["inventory_id", "borrower_user_id"],
            unique=True,
            sqlite_where=sa.text("phase = 'draft'"),
        )
    else:
        op.create_index(
            "uq_loan_draft_per_borrower",
            "loans",
            ["inventory_id", "borrower_user_id"],
            unique=True,
            postgresql_where=sa.text("phase = 'draft'"),
        )


def downgrade() -> None:
    op.drop_index("uq_loan_draft_per_borrower", table_name="loans")

    op.create_table(
        "loan_returns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "loan_return_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_return_id", sa.Integer(), nullable=False),
        sa.Column("loan_line_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["loan_return_id"], ["loan_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loan_line_id"], ["loan_lines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("loans") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="planned")
        )
        batch_op.alter_column("borrower_user_id", new_column_name="responsible_user_id")
        batch_op.alter_column("pickup_on", new_column_name="starts_on")
        batch_op.alter_column("return_on", new_column_name="ends_on")

    op.execute(sa.text("UPDATE loans SET status = 'planned' WHERE phase = 'draft'"))
    op.execute(sa.text("UPDATE loans SET status = 'handed_out' WHERE phase = 'active'"))
    op.execute(sa.text("UPDATE loans SET status = 'closed' WHERE phase = 'closed'"))

    with op.batch_alter_table("loans") as batch_op:
        batch_op.drop_column("phase")
        batch_op.drop_column("contact_user_id")
        batch_op.drop_column("pickup_note")
        batch_op.drop_column("return_note")

    with op.batch_alter_table("loan_lines") as batch_op:
        batch_op.drop_column("replaces_line_id")
        batch_op.drop_column("reason")
        batch_op.drop_column("note")
        batch_op.drop_column("status")

    with op.batch_alter_table("photos") as batch_op:
        batch_op.drop_column("loan_photo_role")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("phone")
