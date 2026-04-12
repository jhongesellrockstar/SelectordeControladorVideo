from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

from driverswitch_gui.services.subprocess_utils import run_hidden

LogFn = Callable[[str], None]


@dataclass(slots=True)
class SystemState:
    computer_name: str
    active_adapter: str
    driver_version: str
    driver_date: str
    inf_name: str
    provider: str
    pnp_device_id: str
    intel_adapter: str
    intel_driver_version: str
    intel_inf_name: str
    intel_provider: str
    intel_pnp_device_id: str
    virtual_adapter: str
    is_admin: bool


class SystemInfoService:
    def __init__(self, log: LogFn | None = None) -> None:
        self.is_windows = platform.system().lower() == "windows"
        self.log = log or (lambda _: None)

    def get_system_state(self) -> SystemState:
        self.log("Iniciando detección del sistema...")
        if not self.is_windows:
            return SystemState(
                computer_name=platform.node() or "Equipo desconocido",
                active_adapter="No disponible",
                driver_version="No disponible",
                driver_date="No disponible",
                inf_name="No disponible",
                provider="No disponible",
                pnp_device_id="",
                intel_adapter="No disponible",
                intel_driver_version="No disponible",
                intel_inf_name="No disponible",
                intel_provider="No disponible",
                intel_pnp_device_id="",
                virtual_adapter="No detectado",
                is_admin=False,
            )

        video = self._run_powershell_json(
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,PNPDeviceID,DriverVersion,DriverDate,Status,InfFilename,AdapterCompatibility | ConvertTo-Json -Depth 4"
        )
        pnp_display = self._run_powershell_json(
            "Get-PnpDevice -Class Display | Select-Object FriendlyName,InstanceId,Status,Class | ConvertTo-Json -Depth 4"
        )
        signed = self._run_powershell_json(
            "Get-CimInstance Win32_PnPSignedDriver | "
            "Where-Object {$_.DeviceClass -eq 'DISPLAY'} | "
            "Select-Object DeviceName,DriverVersion,DriverDate,InfName,Manufacturer,DeviceID | ConvertTo-Json -Depth 4"
        )

        video_list = self._to_list(video)
        pnp_list = self._to_list(pnp_display)
        driver_list = self._to_list(signed)

        intel_video = self._pick_intel_video(video_list)
        virtual_video = self._pick_virtual(video_list)
        default_video = intel_video or self._pick_ok(video_list)

        adapter_name = default_video.get("Name", "No detectado")
        pnp_device_id = default_video.get("PNPDeviceID", "")

        active_driver = self._match_driver(driver_list, pnp_device_id, adapter_name)

        intel_name = intel_video.get("Name", "No detectado")
        intel_pnp = intel_video.get("PNPDeviceID", "")
        intel_driver = self._match_driver(driver_list, intel_pnp, intel_name)

        state = SystemState(
            computer_name=os.environ.get("COMPUTERNAME", platform.node() or "Equipo"),
            active_adapter=adapter_name,
            driver_version=active_driver.get("DriverVersion") or default_video.get("DriverVersion", "No detectado"),
            driver_date=self._normalize_date(active_driver.get("DriverDate") or default_video.get("DriverDate", "")),
            inf_name=active_driver.get("InfName") or default_video.get("InfFilename", "No detectado"),
            provider=active_driver.get("Manufacturer") or default_video.get("AdapterCompatibility", "No detectado"),
            pnp_device_id=pnp_device_id,
            intel_adapter=intel_name,
            intel_driver_version=intel_driver.get("DriverVersion", "No detectado"),
            intel_inf_name=intel_driver.get("InfName", "No detectado"),
            intel_provider=intel_driver.get("Manufacturer", "Intel" if "intel" in intel_name.lower() else "No detectado"),
            intel_pnp_device_id=intel_pnp,
            virtual_adapter=virtual_video.get("Name", "No detectado"),
            is_admin=self._is_admin(),
        )

        self.log(f"Adaptador virtual detectado: {state.virtual_adapter}")
        self.log(f"GPU física Intel detectada: {state.intel_adapter}")
        self.log(f"Driver Intel activo detectado: {state.intel_driver_version}")
        self.log(f"INF Intel activo detectado: {state.intel_inf_name}")
        self.log(f"Modo administrador: {'Sí' if state.is_admin else 'No'}")
        return state

    @staticmethod
    def _to_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [p for p in payload if isinstance(p, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []

    @staticmethod
    def _pick_ok(items: list[dict[str, Any]]) -> dict[str, Any]:
        return next((d for d in items if str(d.get("Status", "")).upper() == "OK"), items[0] if items else {})

    @staticmethod
    def _pick_intel_video(items: list[dict[str, Any]]) -> dict[str, Any]:
        for d in items:
            text = f"{d.get('Name','')} {d.get('AdapterCompatibility','')}".lower()
            if "intel" in text and any(k in text for k in ["uhd", "iris", "graphics"]):
                return d
        for d in items:
            text = f"{d.get('Name','')} {d.get('AdapterCompatibility','')}".lower()
            if "intel" in text:
                return d
        return {}

    @staticmethod
    def _pick_virtual(items: list[dict[str, Any]]) -> dict[str, Any]:
        keys = ["meta", "virtual", "mridd", "indirect display"]
        for d in items:
            text = f"{d.get('Name','')} {d.get('AdapterCompatibility','')}".lower()
            if any(k in text for k in keys):
                return d
        return {}

    @staticmethod
    def _match_driver(drivers: list[dict[str, Any]], pnp: str, name: str) -> dict[str, Any]:
        return next(
            (d for d in drivers if d.get("DeviceID") == pnp or d.get("DeviceName") == name),
            {},
        )

    @staticmethod
    def _normalize_date(raw: str) -> str:
        if not raw:
            return "No detectado"
        text = str(raw)
        if text.startswith("/Date("):
            match = re.search(r"/Date\((\d+)", text)
            if match:
                import datetime

                dt = datetime.datetime.utcfromtimestamp(int(match.group(1)) / 1000)
                return dt.strftime("%Y-%m-%d")
        return text.split("T")[0]

    @staticmethod
    def _is_admin() -> bool:
        if os.name != "nt":
            return False
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _run_powershell_json(self, command: str) -> Any:
        start = time.perf_counter()
        self.log(f"Ejecutando comando PowerShell: {command[:90]}...")
        try:
            proc = run_hidden(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            self.log("Error: comando PowerShell agotó tiempo de espera (30s).")
            return []

        elapsed = (time.perf_counter() - start) * 1000
        self.log(f"Comando finalizado en {elapsed:.0f} ms (código {proc.returncode}).")
        if proc.returncode != 0:
            self.log(f"Advertencia PowerShell stderr: {proc.stderr.strip()[:240]}")
        output = proc.stdout.strip()
        if not output:
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            self.log("Advertencia: salida PowerShell no parseable como JSON.")
            return []
