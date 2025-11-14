"""LAN peer discovery via UDP beacons.

This module provides a lightweight PeerDiscovery class that can announce a signed
beacon and listen for beacons from other peers. Beacons are signed with the
local private key and include `peer_id`, `public_key` and `timestamp`.

For production this uses UDP broadcast; for tests you can provide explicit
target addresses to send beacons directly.
"""
import socket
import threading
import json
import time
import base64
from typing import List, Tuple, Optional

from config import PEER_DISCOVERY_PORT
from utils.crypto_utils import load_keys_for_peer, sign_message, verify_signature, serialize_public_key
from db.db_handler import DBHandler


class PeerDiscovery:
    def __init__(self, peer_id: str, passphrase: bytes, port: int = PEER_DISCOVERY_PORT, interval: float = 5.0, targets: Optional[List[Tuple[str,int]]] = None, use_broadcast: bool = True):
        self.peer_id = peer_id
        self.passphrase = passphrase
        self.port = port
        self.interval = interval
        self.targets = targets or []
        self.use_broadcast = use_broadcast

        self._stop_event = threading.Event()
        self._tx_thread: Optional[threading.Thread] = None
        self._rx_thread: Optional[threading.Thread] = None

        self.db = DBHandler()
        # Load keys for signing and pub
        self.priv, self.pub = load_keys_for_peer(passphrase, peer_id)

    def _build_beacon(self) -> bytes:
        ts = int(time.time())
        pub_pem = serialize_public_key(self.pub)
        payload = json.dumps({"peer_id": self.peer_id, "timestamp": ts, "public_key": base64.b64encode(pub_pem).decode("utf-8")}).encode("utf-8")
        sig = sign_message(self.priv, payload)
        package = json.dumps({"payload": base64.b64encode(payload).decode("utf-8"), "signature": base64.b64encode(sig).decode("utf-8")})
        return package.encode("utf-8")

    def _handle_packet(self, data: bytes, addr):
        try:
            pkg = json.loads(data.decode("utf-8"))
            payload = base64.b64decode(pkg["payload"])
            signature = base64.b64decode(pkg["signature"])
            pl = json.loads(payload.decode("utf-8"))
            remote_pub_pem = base64.b64decode(pl["public_key"])
            # verify signature using remote public key
            ok = verify_signature(load_public_from_pem(remote_pub_pem), payload, signature)
            if not ok:
                return
            peer_id = pl["peer_id"]
            ts = pl["timestamp"]
            # store peer in DB
            self.db.add_peer(peer_id, nickname=None, public_key=remote_pub_pem.decode("utf-8"), fingerprint=None)
            self.db.update_peer_status(peer_id, ts)
        except Exception:
            return

    def _tx_loop(self, sock: socket.socket):
        beacon = self._build_beacon()
        while not self._stop_event.is_set():
            if self.targets:
                for (h,p) in self.targets:
                    try:
                        sock.sendto(beacon, (h,p))
                    except Exception:
                        pass
            elif self.use_broadcast:
                try:
                    sock.sendto(beacon, ("<broadcast>", self.port))
                except Exception:
                    pass
            else:
                # nothing to send
                pass
            time.sleep(self.interval)

    def _rx_loop(self, sock: socket.socket):
        while not self._stop_event.is_set():
            try:
                data, addr = sock.recvfrom(65536)
                if not data:
                    continue
                # ignore our own beacons (optional)
                self._handle_packet(data, addr)
            except socket.timeout:
                continue
            except Exception:
                continue

    def start(self):
        # create TX socket
        tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.use_broadcast:
            tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # create RX socket
        rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rx_sock.bind(("", self.port))
        rx_sock.settimeout(1.0)

        self._tx_thread = threading.Thread(target=self._tx_loop, args=(tx_sock,), daemon=True)
        self._rx_thread = threading.Thread(target=self._rx_loop, args=(rx_sock,), daemon=True)
        self._tx_thread.start()
        self._rx_thread.start()

    def stop(self):
        self._stop_event.set()
        # threads are daemon; allow them a small grace period
        time.sleep(0.2)
        try:
            self.db.close()
        except Exception:
            pass


def load_public_from_pem(pem: bytes):
    # Lazy import to avoid circular deps
    from cryptography.hazmat.primitives import serialization
    return serialization.load_pem_public_key(pem)
