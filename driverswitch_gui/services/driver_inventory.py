from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path

from driverswitch_gui.models import DriverCandidate


class DriverInventoryService:
    def __init__(self) -> None:
        self.is_windows = platform.system().lower() == "windows"

    def list_driver_store(self, active_inf: str = "") -> list[DriverCandidate]:
        if not self.is_windows:
            return []

        proc = subprocess.run(
            ["pnputil", "/enum-drivers", "/class", "Display"],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return []

        blocks = re.split(r"\n\s*\n", proc.stdout)
        drivers: list[DriverCandidate] = []
        for block in blocks:
            published = self._field(block, r"Published Name\s*:\s*(.+)")
            original = self._field(block, r"Original Name\s*:\s*(.+)")
            provider = self._field(block, r"Provider Name\s*:\s*(.+)")
            version_line = self._field(block, r"Driver Version\s*:\s*(.+)")
            signer = self._field(block, r"Signer Name\s*:\s*(.+)")
            if not published:
                continue
            date_part, version_part = self._split_version_line(version_line)
            status = "Disponible"
            if original.lower() == active_inf.lower() or published.lower() == active_inf.lower():
                status = "Activo"
            drivers.append(
                DriverCandidate(
                    source_type="driver_store",
                    provider=provider or "Desconocido",
                    version=version_part or "Desconocida",
                    driver_date=date_part or "Desconocida",
                    inf_name=original or published,
                    published_name=published,
                    signer=signer,
                    status=status,
                )
            )
        return drivers

    def scan_external_folder(self, folder: Path) -> list[DriverCandidate]:
        if not folder.exists() or not folder.is_dir():
            return []

        candidates: list[DriverCandidate] = []
        for inf_path in folder.rglob("*.inf"):
            try:
                content = inf_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not self._is_display_inf(content):
                continue
            version = self._field(content, r"DriverVer\s*=\s*[^,]+,\s*([^\r\n]+)") or "Desconocida"
            date = self._field(content, r"DriverVer\s*=\s*([^,\r\n]+)") or "Desconocida"
            provider = self._field(content, r"Provider\s*=\s*%?([^%\r\n]+)%?") or "Proveedor INF"
            candidates.append(
                DriverCandidate(
                    source_type="external",
                    provider=provider.strip(),
                    version=version.strip(),
                    driver_date=date.strip(),
                    inf_name=inf_path.name,
                    source_path=str(inf_path),
                    status="Disponible (externo)",
                )
            )
        return candidates

    @staticmethod
    def _is_display_inf(content: str) -> bool:
        text = content.lower()
        return "class=display" in text or "{4d36e968-e325-11ce-bfc1-08002be10318}" in text

    @staticmethod
    def _field(text: str, pattern: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _split_version_line(version_line: str) -> tuple[str, str]:
        if "/" in version_line and " " in version_line:
            parts = version_line.split(" ")
            return parts[0], parts[-1]
        if "," in version_line:
            date_part, version_part = version_line.split(",", maxsplit=1)
            return date_part.strip(), version_part.strip()
        return "", version_line.strip()
