from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Resuelve recursos en modo fuente y PyInstaller (onefile/onedir)."""
    rel = Path(relative_path)

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / rel)
        candidates.append(Path(sys.executable).resolve().parent / rel)
    else:
        candidates.append(Path(__file__).resolve().parents[1] / rel)

    for c in candidates:
        if c.exists():
            return c
    return candidates[0] if candidates else Path(relative_path)
