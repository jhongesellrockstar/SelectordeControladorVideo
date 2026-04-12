from __future__ import annotations

import logging
import os
from pathlib import Path


LOG_NAME = "driverswitch"


def build_logger() -> logging.Logger:
    logger = logging.getLogger(LOG_NAME)
    if logger.handlers:
        return logger

    app_data = os.environ.get("APPDATA", str(Path.home()))
    root = Path(app_data) / "DriverSwitchGUI"
    root.mkdir(parents=True, exist_ok=True)
    logfile = root / "driverswitch_technical.log"

    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def technical_log_path() -> Path:
    app_data = os.environ.get("APPDATA", str(Path.home()))
    return Path(app_data) / "DriverSwitchGUI" / "driverswitch_technical.log"
