import sqlite3
import threading
from pathlib import Path
from typing import Optional, Any, List, Tuple, Iterator

from config import DB_PATH
from sync.crdt_engine import CRDTEngine


class Transaction:
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self.conn = conn
        self.lock = lock

    def __enter__(self):
        self.lock.acquire()
        self.conn.execute("BEGIN")
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc:
                self.conn.execute("ROLLBACK")
            else:
                self.conn.execute("COMMIT")
        finally:
            self.lock.release()



class DBHandler:
    """SQLite DB handler for Phase 2.

    Enhancements over prototype:
    - Enable WAL journal and reasonable busy_timeout for concurrency
    - Enforce foreign_keys pragma
    - Transaction context manager
    - Full peer/message CRUD
    - Simple migration/version table
    """

    # File metadata CRUD
    def insert_file_metadata(self, file_name: str, file_path: str, file_hash: str, file_size: int, message_id: str = None, peer_id: str = None, timestamp: int = None) -> int:
        sql = "INSERT INTO file_metadata (file_name, file_path, file_hash, file_size, message_id, peer_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
        cur = self.execute(sql, (file_name, file_path, file_hash, file_size, message_id, peer_id, timestamp))
        return cur.lastrowid

    def get_file_metadata_by_message(self, message_id: str):
        sql = "SELECT * FROM file_metadata WHERE message_id = ?"
        rows = self.query(sql, (message_id,))
        return rows

    def get_file_metadata_by_peer(self, peer_id: str):
        sql = "SELECT * FROM file_metadata WHERE peer_id = ?"
        rows = self.query(sql, (peer_id,))
        return rows

    def __init__(self, db_path: Optional[Path] = None, busy_timeout_ms: int = 5000):
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self.busy_timeout_ms = busy_timeout_ms
        self.crdt_engine = CRDTEngine()

    def connect(self) -> sqlite3.Connection:
        if self._conn:
            return self._conn
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Pragmas for better concurrency
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_ms)};")
        # Enable WAL for improved concurrency
        conn.execute("PRAGMA journal_mode = WAL;")
        self._conn = conn
        return self._conn

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def transaction(self) -> Transaction:
        conn = self.connect()
        return Transaction(conn, self._lock)

    def init_db(self, schema_path: Optional[Path] = None):
        """Initialize DB and apply schema to create needed tables and migration table."""
        conn = self.connect()
        with self._lock:
            if schema_path is None:
                schema_path = Path(__file__).resolve().parent / "schema.sql"
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            # Create a simple migrations table if missing
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    applied_at INTEGER DEFAULT (strftime('%s','now'))
                );
                """
            )
            conn.commit()

    # Generic execute / query helpers
    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        conn = self.connect()
        with self._lock:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur

    def query(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        conn = self.connect()
        with self._lock:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            return rows

    # Peer CRUD
    def add_peer(self, peer_id: str, nickname: Optional[str] = None, public_key: Optional[str] = None, fingerprint: Optional[str] = None):
        sql = "INSERT OR IGNORE INTO peers (peer_id, nickname, public_key, fingerprint) VALUES (?, ?, ?, ?)"
        self.execute(sql, (peer_id, nickname, public_key, fingerprint))

    def get_peer(self, peer_id: str) -> Optional[sqlite3.Row]:
        rows = self.query("SELECT * FROM peers WHERE peer_id = ?", (peer_id,))
        return rows[0] if rows else None

    def get_all_peers(self) -> List[sqlite3.Row]:
        return self.query("SELECT * FROM peers ORDER BY last_seen DESC")

    def update_peer(self, peer_id: str, **fields):
        if not fields:
            return
        keys = ", ".join([f"{k} = ?" for k in fields.keys()])
        params = tuple(fields.values()) + (peer_id,)
        sql = f"UPDATE peers SET {keys} WHERE peer_id = ?"
        self.execute(sql, params)

    def remove_peer(self, peer_id: str):
        self.execute("DELETE FROM peers WHERE peer_id = ?", (peer_id,))

    def update_peer_status(self, peer_id: str, last_seen: int):
        self.update_peer(peer_id, last_seen=last_seen)

    # Message CRUD
    def insert_message(self, peer_id: str, content: bytes, timestamp: int, message_id: str, sync_status: int = 0) -> int:
        sql = "INSERT INTO messages (peer_id, content, timestamp, message_id, sync_status) VALUES (?, ?, ?, ?, ?)"
        cur = self.execute(sql, (peer_id, content, timestamp, message_id, sync_status))
        return cur.lastrowid

    def get_message(self, message_id: str) -> Optional[sqlite3.Row]:
        rows = self.query("SELECT * FROM messages WHERE message_id = ?", (message_id,))
        return rows[0] if rows else None

    def get_messages_by_peer(self, peer_id: str) -> List[sqlite3.Row]:
        sql = "SELECT * FROM messages WHERE peer_id = ? ORDER BY timestamp ASC"
        return self.query(sql, (peer_id,))

    def list_pending_messages(self) -> List[sqlite3.Row]:
        return self.query("SELECT * FROM messages WHERE sync_status = 0 ORDER BY timestamp ASC")

    def update_message_status(self, message_id: str, sync_status: int):
        self.execute("UPDATE messages SET sync_status = ? WHERE message_id = ?", (sync_status, message_id))

    def get_pending_messages_for_peer(self, peer_id: str) -> List[sqlite3.Row]:
        """Return all pending messages for a given peer."""
        return self.query("SELECT * FROM messages WHERE peer_id = ? AND sync_status = 0 ORDER BY timestamp ASC", (peer_id,))

    def retry_pending_messages(self, peer_id: str, send_func, max_retries: int = 5):
        """Attempt to resend all pending messages for a peer with exponential backoff."""
        import time
        pending = self.get_pending_messages_for_peer(peer_id)
        for msg in pending:
            retries = 0
            backoff = 1
            while retries < max_retries:
                success = send_func(msg)
                if success:
                    self.update_message_status(msg["message_id"], 1)  # Mark as sent
                    break
                else:
                    time.sleep(backoff)
                    backoff *= 2
                    retries += 1
            if retries == max_retries:
                print(f"Failed to send message {msg['message_id']} after {max_retries} retries.")

    def mark_message_delivered(self, message_id: str):
        """Mark a message as delivered (sync_status=2)."""
        self.update_message_status(message_id, 2)

    def delete_message(self, message_id: str):
        self.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))

    def sync_messages(self, known_clock: dict) -> List[dict]:
        """
        Synchronize messages using the CRDT engine.
        """
        with self.transaction() as conn:
            # Fetch all messages from the database
            cursor = conn.execute("SELECT id, content, peer_id, timestamp FROM messages")
            db_messages = cursor.fetchall()

            # Add messages to the CRDT engine
            for msg in db_messages:
                self.crdt_engine.add_message(msg["id"], msg["content"], msg["peer_id"])

            # Get missing messages based on the known clock
            missing_messages = self.crdt_engine.get_missing_messages(known_clock)

            return missing_messages


def _quick_demo():
    db = DBHandler()
    db.init_db()
    print(f"DB initialized at {db.db_path}")


if __name__ == "__main__":
    _quick_demo()
