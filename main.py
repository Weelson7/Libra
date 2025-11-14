import argparse
import json
import base64
import hashlib
from getpass import getpass
from pathlib import Path
from typing import Optional, Dict, Any

from config import ensure_dirs, KEY_DIR, key_paths
from utils.logger import get_logger
from utils.crypto_utils import (
    generate_rsa_keypair,
    save_keys_for_peer,
    load_keys_for_peer,
    hybrid_encrypt,
    hybrid_decrypt,
    sign_message,
    verify_signature,
)
from cryptography.hazmat.primitives import serialization
from db.db_handler import DBHandler

logger = get_logger(__name__)


def _fingerprint(pub_pem: bytes) -> str:
    h = hashlib.sha256(pub_pem).hexdigest()
    return h


def _get_passphrase_from_env_or_prompt(env_name: str = "LIBRA_KEY_PASSPHRASE") -> bytes:
    from os import getenv

    p = getenv(env_name)
    if p:
        return p.encode("utf-8")
    # prompt
    pw = getpass("Enter key passphrase: ")
    return pw.encode("utf-8")


def cmd_init(passphrase: Optional[bytes] = None, nickname: Optional[str] = None) -> Dict[str, Any]:
    """Initialize data dirs, DB and generate keys if they don't exist.

    Returns a dict with peer_id and public key path.
    """
    ensure_dirs()
    db = DBHandler()
    db.init_db()

    # Generate keypair
    priv, pub = generate_rsa_keypair(2048)
    pub_pem = pub.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    fp = _fingerprint(pub_pem)
    peer_id = fp[:16]

    if passphrase is None:
        passphrase = _get_passphrase_from_env_or_prompt()

    save_keys_for_peer(priv, pub, passphrase, peer_id)

    # register peer in DB as self
    db.add_peer(peer_id, nickname=nickname or "me", public_key=pub_pem.decode("utf-8"), fingerprint=fp)

    return {"peer_id": peer_id, "public_key_path": str(key_paths(peer_id)[1])}


def cmd_identity(passphrase: Optional[bytes] = None, peer_id: Optional[str] = None) -> Dict[str, Any]:
    """Return identity info (peer_id, public_key PEM, fingerprint)."""
    # derive peer_id if not provided by reading KEY_DIR for available keys
    if peer_id is None:
        # pick first pub key in KEY_DIR
        pks = list(Path(KEY_DIR).glob("*.pub.pem"))
        if not pks:
            raise RuntimeError("No keys found. Run `libra init` first.")
        pub_path = pks[0]
        # strip possible ".pub" suffix in stem
        peer_id = pub_path.stem[:-4] if pub_path.stem.endswith(".pub") else pub_path.stem
    priv, pub = load_keys_for_peer(passphrase or b"", peer_id)
    pub_pem = pub.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    fp = _fingerprint(pub_pem)
    return {"peer_id": peer_id, "public_key_pem": pub_pem.decode("utf-8"), "fingerprint": fp}


def cmd_send_local(message: str, passphrase: Optional[bytes] = None, peer_id: Optional[str] = None) -> Dict[str, Any]:
    """Encrypt and store a local message for the given peer_id (defaults to local key)."""
    # load keys
    if passphrase is None:
        passphrase = _get_passphrase_from_env_or_prompt()
    if peer_id is None:
        # pick any key under KEY_DIR
        pks = list(Path(KEY_DIR).glob("*.pub.pem"))
        if not pks:
            raise RuntimeError("No keys found. Run `libra init` first.")
        peer_id = pks[0].stem[:-4] if pks[0].stem.endswith(".pub") else pks[0].stem

    priv, pub = load_keys_for_peer(passphrase, peer_id)

    # encrypt message for self (store wrapped package)
    package = hybrid_encrypt(pub, message.encode("utf-8"))
    sig = sign_message(priv, message.encode("utf-8"))

    envelope = json.dumps({"package": package, "signature": base64.b64encode(sig).decode("utf-8")}).encode("utf-8")

    db = DBHandler()
    ts = int(__import__("time").time())
    message_id = hashlib.sha256(envelope).hexdigest()[:24]
    db.insert_message(peer_id, envelope, ts, message_id)

    return {"message_id": message_id}


def cmd_read_local(passphrase: Optional[bytes] = None, peer_id: Optional[str] = None) -> Any:
    """Read and decrypt local messages for peer_id (defaults to first key). Returns list of messages dicts."""
    if passphrase is None:
        passphrase = _get_passphrase_from_env_or_prompt()
    if peer_id is None:
        pks = list(Path(KEY_DIR).glob("*.pub.pem"))
        if not pks:
            raise RuntimeError("No keys found. Run `libra init` first.")
        peer_id = pks[0].stem[:-4] if pks[0].stem.endswith(".pub") else pks[0].stem

    priv, pub = load_keys_for_peer(passphrase, peer_id)
    db = DBHandler()
    rows = db.get_messages_by_peer(peer_id)
    out = []
    for r in rows:
        envelope = json.loads(r["content"].decode("utf-8"))
        package = envelope["package"]
        signature = base64.b64decode(envelope["signature"])
        plaintext = hybrid_decrypt(priv, package)
        verified = verify_signature(pub, plaintext, signature)
        out.append({"message_id": r["message_id"], "timestamp": r["timestamp"], "plaintext": plaintext.decode("utf-8"), "verified": verified})
    return out


def build_cli():
    p = argparse.ArgumentParser(prog="libra")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("init")
    sub.add_parser("identity")

    send = sub.add_parser("send-local")
    send.add_argument("message", help="Message text to store locally")

    sub.add_parser("read-local")

    return p


def main(argv=None):
    p = build_cli()
    args = p.parse_args(argv)

    if args.cmd == "init":
        res = cmd_init()
        print("Initialized:", res)
    elif args.cmd == "identity":
        res = cmd_identity()
        print(json.dumps(res, indent=2))
    elif args.cmd == "send-local":
        res = cmd_send_local(args.message)
        print("Stored message:", res)
    elif args.cmd == "read-local":
        res = cmd_read_local()
        print(json.dumps(res, indent=2))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
