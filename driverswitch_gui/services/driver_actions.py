from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Callable

from driverswitch_gui.models import DriverCandidate
from driverswitch_gui.services.system_info import SystemState


class DriverActionService:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.is_windows = platform.system().lower() == "windows"
        self.log = log or (lambda _: None)

    def validate_candidate(self, candidate: DriverCandidate, state: SystemState) -> tuple[bool, str]:
        if not candidate:
            return False, "No hay controlador seleccionado."
        if not candidate.inf_name.lower().endswith(".inf"):
            return False, "El elemento seleccionado no expone un INF válido."
        if candidate.source_type == "external" and not candidate.source_path:
            return False, "La selección externa no tiene ruta de INF."
        if "meta virtual monitor" in state.active_adapter.lower():
            return True, "Se detecta monitor virtual; se recomienda forzar Intel2115 y reiniciar."
        return True, "Compatibilidad básica validada."

    def apply_driver(self, candidate: DriverCandidate) -> tuple[bool, str]:
        if not self.is_windows:
            return False, "La instalación solo está disponible en Windows 11."

        inf_path = self._resolve_inf_path(candidate)
        if not inf_path:
            return False, "No se pudo resolver el INF automáticamente. Usa 'Abrir carpeta' y aplica desde Administrador de dispositivos."

        cmd = ["pnputil", "/add-driver", str(inf_path), "/install"]
        self.log(f"Aplicando controlador con comando: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado al aplicar controlador."

        if proc.returncode == 0:
            self.log(f"Resultado pnputil: {proc.stdout.strip()[:350]}")
            return True, proc.stdout.strip() or "Controlador aplicado correctamente."

        output = (proc.stdout + "\n" + proc.stderr).strip()
        self.log(f"Error pnputil: {output[:400]}")
        return False, output or "No fue posible aplicar el controlador. Ejecuta la app como administrador."

    def refresh_adapter(self, pnp_device_id: str) -> tuple[bool, str]:
        if not self.is_windows:
            return False, "Solo disponible en Windows."
        if not pnp_device_id:
            return False, "No se detectó identificador PNP del adaptador activo."

        cmd = ["pnputil", "/restart-device", pnp_device_id]
        self.log(f"Refrescando adaptador: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado al refrescar el adaptador."

        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Adaptador reiniciado."
        return False, (proc.stdout + "\n" + proc.stderr).strip()

    def apply_and_refresh(self, candidate: DriverCandidate, pnp_device_id: str) -> tuple[bool, str]:
        ok, detail = self.apply_driver(candidate)
        if not ok:
            return False, detail
        ok_refresh, refresh_detail = self.refresh_adapter(pnp_device_id)
        if ok_refresh:
            return True, f"{detail}\n{refresh_detail}"
        return True, f"{detail}\nNo se pudo refrescar automáticamente: {refresh_detail}"

    def request_reboot(self) -> tuple[bool, str]:
        if not self.is_windows:
            return False, "Solo disponible en Windows."
        proc = subprocess.run(["shutdown", "/r", "/t", "5"], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return True, "Reinicio programado en 5 segundos."
        return False, proc.stderr.strip() or "No fue posible programar el reinicio."

    def _resolve_inf_path(self, candidate: DriverCandidate) -> Path | None:
        if candidate.source_path:
            inf = Path(candidate.source_path)
            return inf if inf.exists() else None

        if candidate.published_name:
            try:
                proc = subprocess.run(
                    ["pnputil", "/enum-drivers", "/class", "Display", "/files"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=25,
                    encoding="utf-8",
                    errors="replace",
                )
            except subprocess.TimeoutExpired:
                return None
            if proc.returncode != 0:
                return None
            blocks = proc.stdout.split("\n\n")
            for block in blocks:
                if candidate.published_name.lower() not in block.lower():
                    continue
                for line in block.splitlines():
                    value = line.strip()
                    if value.lower().endswith(".inf") and "\\" in value:
                        path = Path(value)
                        if path.exists():
                            return path
        return None
