"""The packaged Alembic migrations build the same schema as the models."""

import os
import tempfile

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import lamathek.models  # noqa: F401
from lamathek.cli import upgrade_database
from lamathek.db import Base


def _upgraded_engine(tmp: str):
    url = f"sqlite:///{os.path.join(tmp, 'migrated.sqlite3')}"
    upgrade_database(url)
    return create_engine(url)


def test_upgrade_head_on_empty_database_matches_models():
    with tempfile.TemporaryDirectory() as tmp:
        engine = _upgraded_engine(tmp)
        with engine.connect() as conn:
            ctx = MigrationContext.configure(
                conn, opts={"compare_type": True, "render_as_batch": True}
            )
            diff = compare_metadata(ctx, Base.metadata)
        engine.dispose()
    assert diff == [], f"Models and migrations differ: {diff}"


def test_migrated_foreign_keys_match_models():
    """compare_metadata ignores FK ondelete on SQLite; check them explicitly."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = _upgraded_engine(tmp)
        insp = inspect(engine)
        migrated = {
            (table, tuple(fk["constrained_columns"]), fk["referred_table"],
             (fk.get("options") or {}).get("ondelete"))
            for table in insp.get_table_names()
            for fk in insp.get_foreign_keys(table)
        }
        engine.dispose()
    expected = {
        (table.name, tuple(c.name for c in fk.columns),
         fk.elements[0].column.table.name, fk.ondelete)
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_key_constraints
    }
    assert migrated == expected
