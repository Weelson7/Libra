import os
import sys
import tempfile
import importlib
from pathlib import Path


def run_test():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    # Use a temp directory for DB path
    with tempfile.TemporaryDirectory() as td:
        data_dir = Path(td) / "data"
        os.environ["LIBRA_DATA_DIR"] = str(data_dir)

        import config
        importlib.reload(config)

        # ensure dirs
        data, logs, keys = config.ensure_dirs()

        # import DB handler and initialize DB
        from db.db_handler import DBHandler

        db = DBHandler()
        db.init_db()

        # Verify DB file exists
        assert db.db_path.exists(), f"DB file {db.db_path} should exist"

        # Basic check: tables present
        import sqlite3
        conn = sqlite3.connect(str(db.db_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
        expected = {"peers", "devices", "messages", "sync_state"}
        assert expected.issubset(tables), f"Missing expected tables: {expected - tables}"
        # Close DB connections to avoid Windows file-lock on temp cleanup
        conn.close()
        db.close()

    print("test_db: PASS")


if __name__ == "__main__":
    run_test()
