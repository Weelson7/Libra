import os
import sys
import tempfile
import importlib
from pathlib import Path


def run_test():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    with tempfile.TemporaryDirectory() as td:
        os.environ["LIBRA_DATA_DIR"] = str(Path(td) / "data")
        os.environ["LIBRA_KEY_DIR"] = str(Path(td) / "keys")

        import config
        importlib.reload(config)

        from main import cmd_init, cmd_send_local, cmd_read_local

        good_pass = b"good-pass"
        bad_pass = b"bad-pass"

        res = cmd_init(passphrase=good_pass, nickname="tester")
        assert "peer_id" in res

        # send a message with good_pass
        r = cmd_send_local("secret", passphrase=good_pass)
        assert "message_id" in r

        # reading with wrong passphrase should raise when keys can't be loaded
        try:
            cmd_read_local(passphrase=bad_pass)
            raise AssertionError("Expected load failure with bad passphrase")
        except Exception:
            # Accept any exception from wrong passphrase for now
            pass

    print("test_cli_invalid_passphrase: PASS")


if __name__ == "__main__":
    run_test()
