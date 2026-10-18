"""piece event kind and loan links on damages

Revision ID: 20261018_0036
Revises: 20261018_0035
"""

from alembic import op
import sqlalchemy as sa

revision = "20261018_0036"
down_revision = "20261018_0035"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def upgrade() -> None:
    if not _column_exists("damages", "kind"):
        with op.batch_alter_table("damages") as batch:
            batch.add_column(
                sa.Column(
                    "kind", sa.String(length=16), server_default="damage", nullable=False
                )
            )
    if not _column_exists("damages", "loan_id"):
        with op.batch_alter_table("damages") as batch:
            batch.add_column(sa.Column("loan_id", sa.Integer(), nullable=True))
    if not _column_exists("damages", "loan_line_id"):
        with op.batch_alter_table("damages") as batch:
            batch.add_column(sa.Column("loan_line_id", sa.Integer(), nullable=True))

    if not _column_exists("repairs", "resolution_kind"):
        with op.batch_alter_table("repairs") as batch:
            batch.add_column(
                sa.Column(
                    "resolution_kind",
                    sa.String(length=24),
                    server_default="repaired",
                    nullable=False,
                )
            )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO damages (piece_id, recorded_on, note, severe, kind, loan_id, loan_line_id)
            SELECT
                ll.piece_id,
                COALESCE(l.return_on, l.pickup_on, date('now')),
                ll.reason,
                1,
                'total_loss',
                ll.loan_id,
                ll.id
            FROM loan_lines ll
            JOIN loans l ON l.id = ll.loan_id
            WHERE ll.piece_id IS NOT NULL
              AND ll.status = 'not_returned'
              AND NOT EXISTS (
                  SELECT 1 FROM damages d
                  WHERE d.loan_line_id = ll.id AND d.kind = 'total_loss'
              )
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("repairs") as batch:
        batch.drop_column("resolution_kind")
    with op.batch_alter_table("damages") as batch:
        batch.drop_column("loan_line_id")
    with op.batch_alter_table("damages") as batch:
        batch.drop_column("loan_id")
    with op.batch_alter_table("damages") as batch:
        batch.drop_column("kind")
