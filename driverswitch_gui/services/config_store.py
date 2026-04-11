from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class UserConfig:
    preferred_inf: str = ""
    preferred_version: str = ""
    external_paths: list[str] | None = None

    def normalized_paths(self) -> list[str]:
        return self.external_paths or []


class ConfigStore:
    def __init__(self) -> None:
        app_data = os.environ.get("APPDATA", str(Path.home()))
        self.root = Path(app_data) / "DriverSwitchGUI"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "config.json"

    def load(self) -> UserConfig:
        if not self.path.exists():
            return UserConfig(external_paths=[])
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserConfig(external_paths=[])
        return UserConfig(
            preferred_inf=data.get("preferred_inf", ""),
            preferred_version=data.get("preferred_version", ""),
            external_paths=data.get("external_paths", []),
        )

    def save(self, config: UserConfig) -> None:
        payload = asdict(config)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
