from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


SourceType = Literal["driver_store", "external"]


@dataclass(slots=True)
class DriverCandidate:
    source_type: SourceType
    provider: str
    version: str
    driver_date: str
    inf_name: str
    published_name: str = ""
    source_path: str = ""
    signer: str = ""
    status: str = "Disponible"

    @property
    def folder_hint(self) -> Path | None:
        if not self.source_path:
            return None
        path = Path(self.source_path)
        return path.parent if path.exists() else None
