-- Libra DB schema (Phase 2 initial)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS peers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id TEXT NOT NULL UNIQUE,
    nickname TEXT,
    public_key TEXT,
    last_seen INTEGER,
    fingerprint TEXT
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL UNIQUE,
    user_id TEXT,
    device_key TEXT,
    trust_level INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id TEXT NOT NULL,
    content BLOB NOT NULL,
    timestamp INTEGER NOT NULL,
    message_id TEXT NOT NULL UNIQUE,
    sync_status INTEGER DEFAULT 0,
    FOREIGN KEY(peer_id) REFERENCES peers(peer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id TEXT NOT NULL UNIQUE,
    last_sync_timestamp INTEGER,
    vector_clock TEXT
);
