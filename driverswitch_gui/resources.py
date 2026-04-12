from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Resuelve rutas en modo fuente y en modo PyInstaller (_MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parents[1]
    return base / relative_path
