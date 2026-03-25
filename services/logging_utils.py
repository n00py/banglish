from __future__ import annotations

import logging
from pathlib import Path

from .storage_paths import banglish_data_dir, log_path


LOGGER_NAME = "youglish_korean_context_grabber"


def get_logger(addon_dir: Path) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    banglish_data_dir(addon_dir)
    path = log_path(addon_dir)
    try:
        handler = logging.FileHandler(path, encoding="utf-8")
    except Exception:
        handler = logging.NullHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
