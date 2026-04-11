from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path
from typing import Callable

from driverswitch_gui.models import DriverCandidate


class DriverInventoryService:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.is_windows = platform.system().lower() == "windows"
        self.log = log or (lambda _: None)

    def list_driver_store(self, active_inf: str = "") -> list[DriverCandidate]:
        if not self.is_windows:
            return []

        self.log("Leyendo Driver Store (pnputil /enum-drivers /class Display)...")
        try:
            proc = subprocess.run(
                ["pnputil", "/enum-drivers", "/class", "Display"],
                capture_output=True,
                text=True,
                check=False,
                timeout=25,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            self.log("Error: pnputil tardó demasiado al enumerar drivers.")
            return []

        if proc.returncode != 0:
            self.log(f"Error al enumerar drivers: {proc.stderr.strip()[:200]}")
            return []

        drivers: list[DriverCandidate] = []
        for block in re.split(r"\r?\n\s*\r?\n", proc.stdout):
            fields = self._parse_key_values(block)
            published = self._pick(fields, ["published name", "nombre publicado"])
            original = self._pick(fields, ["original name", "nombre original"])
            provider = self._pick(fields, ["provider name", "nombre del proveedor"])
            version_line = self._pick(fields, ["driver version", "versión del controlador"])
            signer = self._pick(fields, ["signer name", "firmante"])
            if not published:
                continue
            date_part, version_part = self._split_version_line(version_line)
            inf_name = original or published
            status = "Activo (sistema)" if inf_name.lower() == active_inf.lower() else "Disponible (store)"
            drivers.append(
                DriverCandidate(
                    source_type="driver_store",
                    provider=provider or "No detectado",
                    version=version_part or "No detectado",
                    driver_date=date_part or "No disponible",
                    inf_name=inf_name,
                    published_name=published,
                    signer=signer,
                    status=status,
                    compatible=True,
                )
            )
        self.log(f"Drivers detectados en store: {len(drivers)}")
        return drivers

    def scan_external_folder(self, folder: Path) -> list[DriverCandidate]:
        if not folder.exists() or not folder.is_dir():
            return []
        self.log(f"Buscando INF externos en: {folder}")
        candidates: list[DriverCandidate] = []
        for inf_path in folder.rglob("*.inf"):
            try:
                content = inf_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not self._is_display_inf(content):
                continue
            version = self._field(content, r"DriverVer\s*=\s*[^,]+,\s*([^\r\n]+)") or "No detectado"
            date = self._field(content, r"DriverVer\s*=\s*([^,\r\n]+)") or "No disponible"
            provider = self._field(content, r"Provider\s*=\s*%?([^%\r\n]+)%?") or "No detectado"
            candidates.append(
                DriverCandidate(
                    source_type="external",
                    provider=provider.strip(),
                    version=version.strip(),
                    driver_date=date.strip(),
                    inf_name=inf_path.name,
                    source_path=str(inf_path),
                    status="Disponible (externo)",
                    compatible=True,
                )
            )
        self.log(f"INF de pantalla encontrados en carpeta externa: {len(candidates)}")
        return candidates

    def autodetect_intel2115(self, roots: list[Path]) -> DriverCandidate | None:
        self.log("Buscando carpeta Intel2115 / iigd_dch.inf...")
        for root in roots:
            if not root.exists() or not root.is_dir():
                continue
            for path in root.rglob("iigd_dch.inf"):
                self.log(f"Carpeta Intel2115 encontrada en: {path}")
                return DriverCandidate(
                    source_type="external",
                    provider="Intel",
                    version="31.0.101.2115",
                    driver_date="No disponible",
                    inf_name=path.name,
                    source_path=str(path),
                    status="Intel2115 detectado",
                    compatible=True,
                )
        self.log("No se encontró iigd_dch.inf en rutas de búsqueda rápidas.")
        return None

    @staticmethod
    def _parse_key_values(block: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
        return fields

    @staticmethod
    def _pick(fields: dict[str, str], candidates: list[str]) -> str:
        for key, value in fields.items():
            for candidate in candidates:
                if candidate in key:
                    return value
        return ""

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
        line = version_line.strip()
        if not line:
            return "", ""
        if "," in line:
            left, right = line.split(",", 1)
            return left.strip(), right.strip()
        parts = line.split()
        if len(parts) >= 2 and "/" in parts[0]:
            return parts[0], parts[-1]
        return "", line
