# Crypto Utilities — Usage

This document explains how to use the helpers in `utils/crypto_utils.py`.

Key helpers
- `generate_rsa_keypair(key_size=2048)` → `(private_key, public_key)`
- `serialize_public_key(pub)` / `load_public_key(pem)`
- `serialize_private_key_encrypted(priv, passphrase)` / `load_private_key_encrypted(pem, passphrase)`

Filesystem helpers
- `save_public_key_file(pub, path)` — write PEM public key to `path`.
- `save_private_key_file_encrypted(priv, passphrase, path)` — write PEM private key encrypted with `passphrase`.
- `load_private_key_file(path, passphrase)` — load encrypted private key from `path`.
- `load_public_key_file(path)` — load public key from `path`.
- `save_keys_for_peer(priv, pub, passphrase, peer_id='local')` — convenience to save keys in `config.KEY_DIR` using `key_paths(peer_id)`.
- `load_keys_for_peer(passphrase, peer_id='local')` — load keys saved by `save_keys_for_peer`.

Encryption / Signing
- `hybrid_encrypt(pub, plaintext, aad=None)` → JSON package string (base64 fields)
- `hybrid_decrypt(priv, package_json, aad=None)` → plaintext
- `sign_message(priv, data)` → signature bytes
- `verify_signature(pub, data, signature)` → bool

Recommendations
- Protect private key passphrases with a secure prompt or OS key store.
- Rotate keys occasionally and provide an import/export key flow.
- Consider binary packaging of encrypted payloads for production.
