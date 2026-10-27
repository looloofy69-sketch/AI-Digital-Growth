"""Apply numbered SQL migrations transactionally to a disposable PostgreSQL database."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("psycopg is required; install the postgres optional dependency", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    migrations = sorted((root / "db" / "migrations").glob("[0-9][0-9][0-9][0-9]_*.sql"))
    if not migrations:
        print("No numbered SQL migrations found", file=sys.stderr)
        return 2
    with psycopg.connect(dsn) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        for migration in migrations:
            version = migration.name
            if conn.execute("SELECT 1 FROM schema_migrations WHERE version=%s", (version,)).fetchone():
                print(f"SKIP {version}: already applied")
                continue
            with conn.transaction():
                psycopg.ClientCursor(conn).execute(migration.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (version,))
            print(f"APPLIED {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
