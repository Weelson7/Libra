import os
import sys
import tempfile
import importlib
from pathlib import Path
import time
import threading
import random


def run_test():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    with tempfile.TemporaryDirectory() as td:
        os.environ["LIBRA_DATA_DIR"] = str(Path(td) / "data")
        import config
        importlib.reload(config)

        from db.db_handler import DBHandler

        db = DBHandler()
        db.init_db()
        # Ensure peer exists so FK constraints do not fail
        db.add_peer("peer-concurrent", nickname="Concurrent")

        NUM_THREADS = 8
        MSGS_PER_THREAD = 200

        def worker(tid: int):
            for i in range(MSGS_PER_THREAD):
                ts = int(time.time())
                msgid = f"t{tid}-{i}-{random.randint(0,999999)}"
                # Insert with small sleeps to increase contention
                db.insert_message("peer-concurrent", b"x" * 16, ts, msgid)
                if i % 50 == 0:
                    time.sleep(0.01)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_THREADS)]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            msgs = db.get_messages_by_peer("peer-concurrent")
            total = len(msgs)
            expected = NUM_THREADS * MSGS_PER_THREAD
            assert total == expected, f"Expected {expected} messages, got {total}"
        finally:
            # Ensure DB is closed even if assertion fails to avoid file-lock on Windows
            try:
                db.close()
            except Exception:
                pass

    print("test_db_concurrency: PASS")


if __name__ == "__main__":
    run_test()
