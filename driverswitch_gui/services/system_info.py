from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable


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


class SystemInfoService:
    def __init__(self, log: LogFn | None = None) -> None:
        self.is_windows = platform.system().lower() == "windows"
        self.log = log or (lambda _: None)

    def get_system_state(self) -> SystemState:
        self.log("Iniciando detección del sistema...")
        if not self.is_windows:
            return SystemState(
                computer_name=platform.node() or "Equipo desconocido",
                active_adapter="No disponible fuera de Windows",
                driver_version="No disponible",
                driver_date="No disponible",
                inf_name="No disponible",
                provider="No disponible",
                pnp_device_id="",
            )

        video = self._run_powershell_json(
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,PNPDeviceID,DriverVersion,DriverDate,Status,InfFilename,AdapterCompatibility | "
            "ConvertTo-Json -Depth 4"
        )
        pnp_display = self._run_powershell_json(
            "Get-PnpDevice -Class Display | "
            "Select-Object FriendlyName,InstanceId,Status,Class | ConvertTo-Json -Depth 4"
        )
        signed_drivers = self._run_powershell_json(
            "Get-CimInstance Win32_PnPSignedDriver | "
            "Where-Object {$_.DeviceClass -eq 'DISPLAY'} | "
            "Select-Object DeviceName,DriverVersion,DriverDate,InfName,Manufacturer,DeviceID | "
            "ConvertTo-Json -Depth 4"
        )

        video_list = self._to_list(video)
        pnp_list = self._to_list(pnp_display)
        driver_list = self._to_list(signed_drivers)

        active_video = next((d for d in video_list if str((d or {}).get("Status", "")).upper() == "OK"), video_list[0] if video_list else {})
        active_pnp = next((d for d in pnp_list if str((d or {}).get("Status", "")).upper() == "OK"), pnp_list[0] if pnp_list else {})

        adapter_name = (active_video or {}).get("Name") or (active_pnp or {}).get("FriendlyName") or "No detectado"
        pnp_device_id = (active_video or {}).get("PNPDeviceID") or (active_pnp or {}).get("InstanceId") or ""

        active_driver = next(
            (
                d
                for d in driver_list
                if (d or {}).get("DeviceID") == pnp_device_id
                or (d or {}).get("DeviceName") == adapter_name
            ),
            driver_list[0] if driver_list else {},
        )

        state = SystemState(
            computer_name=os.environ.get("COMPUTERNAME", platform.node() or "Equipo"),
            active_adapter=adapter_name,
            driver_version=(active_driver or {}).get("DriverVersion") or (active_video or {}).get("DriverVersion", "No detectado"),
            driver_date=self._normalize_date((active_driver or {}).get("DriverDate") or (active_video or {}).get("DriverDate", "")),
            inf_name=(active_driver or {}).get("InfName") or (active_video or {}).get("InfFilename", "No detectado"),
            provider=(active_driver or {}).get("Manufacturer") or (active_video or {}).get("AdapterCompatibility", "No detectado"),
            pnp_device_id=pnp_device_id,
        )
        self.log(f"GPU principal detectada: {state.active_adapter}")
        self.log(f"Driver activo detectado: {state.driver_version}")
        self.log(f"INF activo detectado: {state.inf_name}")
        return state

    @staticmethod
    def _to_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [p for p in payload if isinstance(p, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []

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

    def _run_powershell_json(self, command: str) -> Any:
        start = time.perf_counter()
        self.log(f"Ejecutando comando PowerShell: {command[:80]}...")
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                check=False,
                timeout=25,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            self.log("Error: comando PowerShell agotó el tiempo de espera (25s).")
            return []

        elapsed = (time.perf_counter() - start) * 1000
        self.log(f"Comando finalizado en {elapsed:.0f} ms (código {proc.returncode}).")
        output = proc.stdout.strip()
        if proc.returncode != 0:
            self.log(f"Advertencia PowerShell stderr: {proc.stderr.strip()[:240]}")
        if not output:
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            self.log("Advertencia: no se pudo parsear salida JSON de PowerShell.")
            return []
