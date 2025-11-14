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
