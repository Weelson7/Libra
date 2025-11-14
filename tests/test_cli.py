import os
import sys
import tempfile
import importlib
from pathlib import Path


def run_test():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    # Use temp dirs for data and keys
    with tempfile.TemporaryDirectory() as td:
        os.environ["LIBRA_DATA_DIR"] = str(Path(td) / "data")
        os.environ["LIBRA_KEY_DIR"] = str(Path(td) / "keys")

        import config
        importlib.reload(config)

        from main import cmd_init, cmd_identity, cmd_send_local, cmd_read_local

        passphrase = b"cli-pass"

        res_init = cmd_init(passphrase=passphrase, nickname="tester")
        assert "peer_id" in res_init

        info = cmd_identity(passphrase=passphrase)
        assert info["fingerprint"]

        # send local message
        msg = "Hello from CLI"
        r = cmd_send_local(msg, passphrase=passphrase)
        assert "message_id" in r

        out = cmd_read_local(passphrase=passphrase)
        assert any(m["plaintext"] == msg for m in out), f"Expected message in {out}"

    print("test_cli: PASS")


if __name__ == "__main__":
    run_test()
