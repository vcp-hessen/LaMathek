"""loan journal entries

Revision ID: 20261018_0037
Revises: 20261018_0036
"""

from alembic import op
import sqlalchemy as sa

revision = "20261018_0037"
down_revision = "20261018_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loan_journal_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(datetime('now'))"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), server_default="{}", nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.Column("piece_id", sa.Integer(), nullable=True),
        sa.Column("loan_line_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["piece_id"], ["pieces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["loan_line_id"], ["loan_lines.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_loan_journal_entries_loan_id",
        "loan_journal_entries",
        ["loan_id"],
    )
    op.create_index(
        "ix_loan_journal_entries_piece_id",
        "loan_journal_entries",
        ["piece_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_loan_journal_entries_piece_id", table_name="loan_journal_entries")
    op.drop_index("ix_loan_journal_entries_loan_id", table_name="loan_journal_entries")
    op.drop_table("loan_journal_entries")
