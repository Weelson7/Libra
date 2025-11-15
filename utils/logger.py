import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(name: str = "libra", level: str | None = None):
    try:
        from config import LOG_DIR, LOG_LEVEL
    except Exception:
        LOG_DIR = Path("./logs")
        LOG_LEVEL = "DEBUG"

    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    lvl = level or LOG_LEVEL
    numeric_level = getattr(logging, str(lvl).upper(), logging.DEBUG)
    logger.setLevel(numeric_level)

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = RotatingFileHandler(log_dir / "libra.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

def audit_metadata_leaks(data: dict) -> bool:
    """Stub for auditing metadata leaks."""
    # Scan for IP, timestamps, or other identifying info
    return True  # Return False if leak detected
# Add log sanitization for sensitive data
import re

SENSITIVE_PATTERNS = [r'pass(word)?', r'key', r'secret', r'token']

def sanitize_log_message(msg):
    for pat in SENSITIVE_PATTERNS:
        msg = re.sub(pat, '[REDACTED]', msg, flags=re.IGNORECASE)
    return msg

# Patch get_logger to sanitize messages
_original_setup_logging = setup_logging

def setup_logging(name: str = "libra", level: str | None = None):
    logger = _original_setup_logging(name, level)
    class SanitizedLogger(logging.Logger):
        def info(self, msg, *args, **kwargs):
            super().info(sanitize_log_message(msg), *args, **kwargs)
        def warning(self, msg, *args, **kwargs):
            super().warning(sanitize_log_message(msg), *args, **kwargs)
        def error(self, msg, *args, **kwargs):
            super().error(sanitize_log_message(msg), *args, **kwargs)
        def debug(self, msg, *args, **kwargs):
            super().debug(sanitize_log_message(msg), *args, **kwargs)
    logger.__class__ = SanitizedLogger
    return logger
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(name: str = "libra", level: str | None = None):
    try:
        from config import LOG_DIR, LOG_LEVEL
    except Exception:
        LOG_DIR = Path("./logs")
        LOG_LEVEL = "DEBUG"

    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    lvl = level or LOG_LEVEL
    numeric_level = getattr(logging, str(lvl).upper(), logging.DEBUG)
    logger.setLevel(numeric_level)

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = RotatingFileHandler(log_dir / "libra.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


def get_logger(name: str = "libra"):
    return setup_logging(name)
