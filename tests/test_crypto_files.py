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
        save_keys_for_peer,
        load_keys_for_peer,
        hybrid_encrypt,
        hybrid_decrypt,
        sign_message,
        verify_signature,
    )

    passphrase = b"file-pass"

    with tempfile.TemporaryDirectory() as td:
        # override KEY_DIR to temp for this test
        os.environ["LIBRA_KEY_DIR"] = str(Path(td) / "keys")
        importlib.reload(config)

        priv, pub = generate_rsa_keypair()
        # Save keys using helper
        priv_path, pub_path = save_keys_for_peer(priv, pub, passphrase, peer_id="testpeer")

        # Load keys back
        loaded_priv, loaded_pub = load_keys_for_peer(passphrase, peer_id="testpeer")

        msg = b"file-backed message"
        pkg = hybrid_encrypt(loaded_pub, msg)
        pt = hybrid_decrypt(loaded_priv, pkg)
        assert pt == msg

        sig = sign_message(loaded_priv, msg)
        assert verify_signature(loaded_pub, msg, sig)

    print("test_crypto_files: PASS")


if __name__ == "__main__":
    run_test()
