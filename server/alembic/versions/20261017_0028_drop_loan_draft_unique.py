"""drop one-draft-per-borrower unique index

Revision ID: 20261017_0028
Revises: 20261017_0027
"""

from alembic import op

revision = "20261017_0028"
down_revision = "20261017_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_loan_draft_per_borrower", table_name="loans")


def downgrade() -> None:
    import sqlalchemy as sa

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
