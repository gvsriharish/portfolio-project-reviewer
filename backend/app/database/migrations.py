"""Lightweight idempotent schema migrations.

The project intentionally avoids a heavy migration framework. Existing
SQLite databases (created before Phases 2–5) are upgraded in place by
adding missing columns; `CREATE TABLE` for new tables is already handled
by `Base.metadata.create_all`. Every statement is applied defensively so
that re-running against an up-to-date database is a no-op.
"""
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# (table, column, DDL fragment)
COLUMN_MIGRATIONS = [
    ("findings", "finding_key", "VARCHAR(300)"),
    ("finding_evidence", "finding_key", "VARCHAR(300)"),
    ("recommendations", "finding_id", "VARCHAR(36)"),
    ("recommendations", "status", "VARCHAR(30) DEFAULT 'OPEN' NOT NULL"),
    ("recommendations", "expected_change", "TEXT DEFAULT '' NOT NULL"),
    ("analysis_runs", "metrics", "JSON"),
    ("analysis_runs", "commit_sha", "VARCHAR(100)"),
    ("analysis_runs", "branch", "VARCHAR(200)"),
]


def run_migrations(engine: Engine) -> None:
    for table, column, ddl in COLUMN_MIGRATIONS:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                conn.commit()
                logger.info("Migration applied: %s.%s added", table, column)
        except Exception:
            # Column already exists (or table not yet created) — safe to ignore.
            pass
