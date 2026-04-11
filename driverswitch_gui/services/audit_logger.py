from __future__ import annotations

import logging
import os
from pathlib import Path


def build_logger() -> logging.Logger:
    logger = logging.getLogger("driverswitch")
    if logger.handlers:
        return logger

    app_data = os.environ.get("APPDATA", str(Path.home()))
    root = Path(app_data) / "DriverSwitchGUI"
    root.mkdir(parents=True, exist_ok=True)
    logfile = root / "driverswitch.log"

    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
