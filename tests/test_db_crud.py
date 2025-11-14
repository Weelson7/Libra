import os
import sys
import tempfile
import importlib
from pathlib import Path
import time


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

        # Peer CRUD
        db.add_peer("peerA", nickname="Alice", public_key="PUBKEYA", fingerprint="FP1")
        db.add_peer("peerB", nickname="Bob", public_key="PUBKEYB", fingerprint="FP2")

        p = db.get_peer("peerA")
        assert p is not None and p["nickname"] == "Alice"

        all_peers = db.get_all_peers()
        assert len(all_peers) >= 2

        db.update_peer("peerA", nickname="Alice2")
        p2 = db.get_peer("peerA")
        assert p2["nickname"] == "Alice2"

        # Message CRUD
        ts = int(time.time())
        msg_id = "m1"
        db.insert_message("peerA", b"hello", ts, msg_id)
        msg = db.get_message(msg_id)
        assert msg is not None and msg["message_id"] == msg_id

        msgs = db.get_messages_by_peer("peerA")
        assert len(msgs) == 1

        pending = db.list_pending_messages()
        assert any(m["message_id"] == msg_id for m in pending)

        db.update_message_status(msg_id, 1)
        msg_after = db.get_message(msg_id)
        assert msg_after["sync_status"] == 1

        db.delete_message(msg_id)
        assert db.get_message(msg_id) is None

        # Remove peer and ensure cascade (messages linked to peer should be removed)
        # Insert message again, then remove peer and check messages deleted via FK cascade
        db.insert_message("peerA", b"hello2", ts, "m2")
        assert db.get_message("m2") is not None
        db.remove_peer("peerA")
        assert db.get_peer("peerA") is None
        # message should be deleted by cascade
        assert db.get_message("m2") is None

        # Cleanup
        db.close()

    print("test_db_crud: PASS")


if __name__ == "__main__":
    run_test()
