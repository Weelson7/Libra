import os
import sys
import tempfile
import importlib
from pathlib import Path


def run_test():
    # Create a temporary dir to act as LIBRA_DATA_DIR
    with tempfile.TemporaryDirectory() as td:
        data_dir = os.path.join(td, "data")
        log_dir = os.path.join(td, "logs")
        # Set env vars before importing config
        os.environ["LIBRA_DATA_DIR"] = data_dir
        os.environ["LIBRA_LOG_DIR"] = log_dir

        # Ensure project root is on sys.path so `import config` finds the module
        project_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(project_root))

        # Import (or reload) config so it picks up env vars
        import config
        importlib.reload(config)

        # Ensure dirs
        d, l, k = config.ensure_dirs()

        assert d.exists(), f"data dir {d} should exist"
        assert l.exists(), f"log dir {l} should exist"
        assert k.exists(), f"key dir {k} should exist"

        # Test key_paths helper
        priv, pub = config.key_paths("testpeer")
        assert str(priv).endswith("testpeer.priv.pem")
        assert str(pub).endswith("testpeer.pub.pem")

        # Validate config
        assert config.validate_config() is True

    print("test_config: PASS")


if __name__ == "__main__":
    run_test()
