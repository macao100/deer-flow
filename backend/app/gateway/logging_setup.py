"""
Unified file logging for DeerFlow — writes everything to logs/deerflow.log.
Call setup_file_logging() once at gateway startup (lifespan).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_INSTALLED = False


def setup_file_logging(log_dir: str, level: int = logging.DEBUG) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "deerflow.log")

    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.addHandler(handler)
    # Ensure root captures DEBUG so the file handler receives everything
    if root.level == logging.NOTSET or root.level > level:
        root.setLevel(level)

    # Silence chatty loggers that pollute the debug log
    for noisy in ("httpx", "httpcore", "urllib3", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("deerflow.logging").info("File logging active → %s", log_path)
