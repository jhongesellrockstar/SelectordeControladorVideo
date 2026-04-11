from __future__ import annotations

from dataclasses import dataclass, field
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
    compatible: bool = True

    @property
    def folder_hint(self) -> Path | None:
        if not self.source_path:
            return None
        path = Path(self.source_path)
        return path.parent if path.exists() else None


@dataclass(slots=True)
class ProfileData:
    sections: dict[str, dict[str, str]] = field(default_factory=dict)

    def get(self, section: str, key: str, default: str = "") -> str:
        return self.sections.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: str) -> None:
        self.sections.setdefault(section, {})[key] = value


@dataclass(slots=True)
class ProfileComparison:
    matches: bool
    details: list[str]
