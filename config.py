import os
from pathlib import Path
from pathlib import Path
import os
from typing import Tuple

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("LIBRA_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.getenv("LIBRA_DB_PATH", DATA_DIR / "libra.db"))
LOG_DIR = Path(os.getenv("LIBRA_LOG_DIR", BASE_DIR / "logs"))

# Network defaults
PEER_DISCOVERY_PORT = int(os.getenv("LIBRA_PEER_DISCOVERY_PORT", "37020"))
HTTP_PORT = int(os.getenv("LIBRA_HTTP_PORT", "8443"))
    
# Tor configuration
TOR_ENABLED = True
_proj_utils = Path(__file__).parent / "utils"
# Try common locations for tor executable inside the `utils` directory
if (_proj_utils / "tor.exe").exists():
    TOR_PATH = str(_proj_utils / "tor.exe")
elif (_proj_utils / "tor" / "tor.exe").exists():
    TOR_PATH = str(_proj_utils / "tor" / "tor.exe")
else:
    # look for bundled expert bundle under utils
    found = None
    for p in _proj_utils.iterdir():
        if p.is_dir() and p.name.startswith('tor-expert-bundle'):
            candidate = p / 'tor' / 'tor.exe'
            if candidate.exists():
                found = candidate
                break
    if found:
        TOR_PATH = str(found)
    else:
        # fallback to system tor on PATH
        TOR_PATH = 'tor'
TOR_CONTROL_PORT = 9051
TOR_PASSWORD = None  # Set if Tor control port is password protected
TOR_CIRCUIT_TIMEOUT = 30  # seconds

# Key storage
KEY_DIR = Path(os.getenv("LIBRA_KEY_DIR", DATA_DIR / "keys"))


# Logging / runtime
LOG_LEVEL = os.getenv("LIBRA_LOG_LEVEL", "DEBUG")
DEBUG = os.getenv("LIBRA_DEBUG", "1") in ("1", "true", "True", "yes")


def ensure_dirs():
    """Create data/log directories if missing and return their paths."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR, LOG_DIR, KEY_DIR


def key_paths(peer_id: str = "local") -> Tuple[Path, Path]:
    """Return (private_key_path, public_key_path) for a given peer/device id."""
    priv = KEY_DIR / f"{peer_id}.priv.pem"
    pub = KEY_DIR / f"{peer_id}.pub.pem"
    return priv, pub


def validate_config():
    """Perform basic runtime validation of config values.

    Raises ValueError on invalid config.
    """
    if not (1 <= PEER_DISCOVERY_PORT <= 65535):
        raise ValueError("PEER_DISCOVERY_PORT must be 1..65535")
    if not (1 <= HTTP_PORT <= 65535):
        raise ValueError("HTTP_PORT must be 1..65535")
    # Ensure DB parent directory exists or is creatable
    db_parent = DB_PATH.parent
    if not db_parent.exists():
        try:
            db_parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create DB directory {db_parent}: {e}")
    return True


if __name__ == "__main__":
    print("LIBRA config:")
    print("BASE_DIR:", BASE_DIR)
    print("DATA_DIR:", DATA_DIR)
    print("DB_PATH:", DB_PATH)
    print("LOG_DIR:", LOG_DIR)
    print("LOG_LEVEL:", LOG_LEVEL)
