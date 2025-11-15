# Device metadata and trust management for multi-device sync
import sqlite3
from typing import List, Optional, Dict

class DeviceManager:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            user_id TEXT,
            device_key TEXT,
            trust_level INTEGER,
            name TEXT,
            last_active TIMESTAMP
        )''')
        self.conn.commit()

    def link_device(self, device_id: str, user_id: str, device_key: str, name: str, trust_level: int = 1):
        cur = self.conn.cursor()
        cur.execute('''
        INSERT OR REPLACE INTO devices (device_id, user_id, device_key, trust_level, name, last_active)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (device_id, user_id, device_key, trust_level, name))
        self.conn.commit()

    def revoke_device(self, device_id: str):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
        self.conn.commit()

    def rename_device(self, device_id: str, new_name: str):
        cur = self.conn.cursor()
        cur.execute('UPDATE devices SET name = ? WHERE device_id = ?', (new_name, device_id))
        self.conn.commit()

    def get_devices(self, user_id: str) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute('SELECT device_id, name, trust_level, last_active FROM devices WHERE user_id = ?', (user_id,))
        rows = cur.fetchall()
        return [dict(device_id=row[0], name=row[1], trust_level=row[2], last_active=row[3]) for row in rows]

    def update_last_active(self, device_id: str):
        cur = self.conn.cursor()
        cur.execute('UPDATE devices SET last_active = CURRENT_TIMESTAMP WHERE device_id = ?', (device_id,))
        self.conn.commit()
