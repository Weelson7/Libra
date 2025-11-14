import os
import sys
import tempfile
import importlib
from pathlib import Path


def run_test():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    import config
    importlib.reload(config)

    from utils.crypto_utils import (
        generate_rsa_keypair,
        serialize_public_key,
        serialize_private_key_encrypted,
        load_private_key_encrypted,
        load_public_key,
        hybrid_encrypt,
        hybrid_decrypt,
        sign_message,
        verify_signature,
    )

    # generate keys
    priv, pub = generate_rsa_keypair(2048)

    # serialize public key and reload
    pub_pem = serialize_public_key(pub)
    pub2 = load_public_key(pub_pem)

    # serialize private key encrypted to disk and reload
    passphrase = b"test-passphrase"
    priv_pem = serialize_private_key_encrypted(priv, passphrase)

    with tempfile.TemporaryDirectory() as td:
        keyfile = Path(td) / "priv.pem"
        keyfile.write_bytes(priv_pem)

        loaded_priv = load_private_key_encrypted(keyfile.read_bytes(), passphrase)

        # hybrid encrypt/decrypt
        msg = b"hello libra crypto"
        package = hybrid_encrypt(pub2, msg)
        pt = hybrid_decrypt(loaded_priv, package)
        assert pt == msg

        # signing
        sig = sign_message(loaded_priv, msg)
        ok = verify_signature(pub2, msg, sig)
        assert ok is True

    print("test_crypto: PASS")


if __name__ == "__main__":
    run_test()
