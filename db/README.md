# Libra Database

This directory contains the SQLite schema and migration helpers for Libra.

Files:
- `schema.sql` — canonical SQL schema used by `DBHandler.init_db()`.
- `migrations/` — numbered SQL migration files applied in order by `migrate.py`.
- `db_handler.py` — `DBHandler` (connection helpers, CRUD, WAL setup).

Usage

Basic initialization is handled by `DBHandler.init_db()` which applies `schema.sql` and ensures the `schema_version` table exists.

To apply incremental migrations (recommended for upgrades), run:

```powershell
python db\migrate.py
```

The migration runner will execute any `*.sql` files in `db/migrations/` that have not yet been recorded in the database `schema_version` table.

Notes

- The DB uses `PRAGMA journal_mode = WAL` and `PRAGMA foreign_keys = ON`.
- For concurrency in-process, `DBHandler` uses a threading lock combined with `busy_timeout` to reduce contention.
- For high-scale deployments, consider moving to a server-backed database.
