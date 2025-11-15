"""Simple migration runner for db/migrations.

This script applies numbered SQL files in `db/migrations/` in lexical order
and records applied migrations in the `schema_version` table.
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DB_PATH


def ensure_schema_table(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at INTEGER DEFAULT (strftime('%s','now'))
        );
        """
    )
    conn.commit()


def applied_versions(conn: sqlite3.Connection):
    cur = conn.execute("SELECT version FROM schema_version")
    return {row[0] for row in cur.fetchall()}


def apply_migration(conn: sqlite3.Connection, version: str, sql: str):
    print(f"Applying migration {version}")
    conn.executescript(sql)
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    conn.commit()


def main():
    db = Path(DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row

        ensure_schema_table(conn)
        applied = applied_versions(conn)

        migrations_dir = Path(__file__).resolve().parent / "migrations"
        if not migrations_dir.exists():
            print("No migrations directory found")
            return

        files = sorted(migrations_dir.glob("*.sql"))
        for f in files:
            ver = f.name
            if ver in applied:
                print(f"Skipping already applied {ver}")
                continue
            sql = f.read_text(encoding="utf-8")
            apply_migration(conn, ver, sql)

        print("Migrations complete")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
