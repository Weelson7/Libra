"""Cryptography utilities for Libra (Phase 3).

Implements:
- RSA key generation and serialization
- Private key encryption (BestAvailableEncryption)
- Hybrid encryption: AES-GCM + RSA-OAEP
- Message signing (RSA-PSS) and verification

This module uses the `cryptography` package.
"""
from __future__ import annotations

import json
import base64
import os
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import constant_time
from pathlib import Path

from config import KEY_DIR, key_paths


def generate_rsa_keypair(key_size: int = 2048) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate an RSA private/public keypair."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    pub = priv.public_key()
    return priv, pub


def serialize_public_key(pub: rsa.RSAPublicKey) -> bytes:
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_public_key(pem: bytes) -> rsa.RSAPublicKey:
    return serialization.load_pem_public_key(pem)


def serialize_private_key_encrypted(priv: rsa.RSAPrivateKey, passphrase: bytes) -> bytes:
    """Serialize private key to PEM encrypted with provided passphrase (bytes)."""
    return priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )


def load_private_key_encrypted(pem: bytes, passphrase: bytes) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(pem, password=passphrase)


def hybrid_encrypt(pub: rsa.RSAPublicKey, plaintext: bytes, aad: bytes | None = None) -> str:
    """Encrypt data for recipient public key using hybrid RSA-OAEP + AES-GCM.

    Returns a JSON string with base64 fields: enc_key, nonce, ciphertext
    """
    # Generate random AES key
    aes_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(aes_key)
    # 12-byte nonce for AES-GCM
    nonce = os.urandom(12)

    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

    # Encrypt AES key with RSA-OAEP
    enc_key = pub.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    package = {
        "enc_key": base64.b64encode(enc_key).decode("utf-8"),
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        "aad": base64.b64encode(aad).decode("utf-8") if aad else None,
    }
    return json.dumps(package)


def hybrid_decrypt(priv: rsa.RSAPrivateKey, package_json: str, aad: bytes | None = None) -> bytes:
    pkg = json.loads(package_json)
    enc_key = base64.b64decode(pkg["enc_key"])
    nonce = base64.b64decode(pkg["nonce"])
    ciphertext = base64.b64decode(pkg["ciphertext"])
    if aad is None and pkg.get("aad"):
        aad = base64.b64decode(pkg.get("aad"))

    # Decrypt AES key
    aes_key = priv.decrypt(
        enc_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    aesgcm = AESGCM(aes_key)
    pt = aesgcm.decrypt(nonce, ciphertext, aad)
    return pt


def sign_message(priv: rsa.RSAPrivateKey, data: bytes) -> bytes:
    sig = priv.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return sig


def verify_signature(pub: rsa.RSAPublicKey, data: bytes, signature: bytes) -> bool:
    try:
        pub.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# Filesystem helpers
def save_public_key_file(pub: rsa.RSAPublicKey, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pem = serialize_public_key(pub)
    path.write_bytes(pem)


def save_private_key_file_encrypted(priv: rsa.RSAPrivateKey, passphrase: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pem = serialize_private_key_encrypted(priv, passphrase)
    path.write_bytes(pem)


def load_private_key_file(path: Path, passphrase: bytes) -> rsa.RSAPrivateKey:
    data = path.read_bytes()
    return load_private_key_encrypted(data, passphrase)


def load_public_key_file(path: Path) -> rsa.RSAPublicKey:
    data = path.read_bytes()
    return load_public_key(data)


def save_keys_for_peer(priv: rsa.RSAPrivateKey, pub: rsa.RSAPublicKey, passphrase: bytes, peer_id: str = "local") -> Tuple[Path, Path]:
    priv_path, pub_path = key_paths(peer_id)
    save_private_key_file_encrypted(priv, passphrase, priv_path)
    save_public_key_file(pub, pub_path)
    return priv_path, pub_path


def load_keys_for_peer(passphrase: bytes, peer_id: str = "local") -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    priv_path, pub_path = key_paths(peer_id)
    priv = load_private_key_file(priv_path, passphrase)
    pub = load_public_key_file(pub_path)
    return priv, pub
