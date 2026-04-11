from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from driverswitch_gui.models import DriverCandidate
from driverswitch_gui.services.system_info import SystemState

TARGET_VERSION = "31.0.101.2115"


@dataclass(slots=True)
class ApplyPlan:
    target_device: str
    target_pnp: str
    inf_path: str
    source_reason: str
    using_preferred: bool


class DriverActionService:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.is_windows = platform.system().lower() == "windows"
        self.log = log or (lambda _: None)

    def validate_candidate(
        self,
        candidate: DriverCandidate,
        state: SystemState,
        preferred_inf_path: str = "",
    ) -> tuple[bool, str, ApplyPlan | None]:
        if not state.is_admin:
            return False, "La aplicación no está en modo administrador.", None
        if not candidate:
            return False, "No hay controlador seleccionado.", None
        if not state.intel_adapter or state.intel_adapter == "No detectado":
            return False, "No se detectó Intel(R) UHD Graphics como dispositivo objetivo.", None

        inf_path = self._resolve_inf_path(candidate)
        if not inf_path:
            return False, "No se pudo resolver la ruta del INF seleccionado.", None

        reason = "selección manual en tabla"
        using_preferred = False
        if preferred_inf_path and Path(preferred_inf_path).exists() and Path(preferred_inf_path).resolve() == inf_path.resolve():
            reason = "coincide con perfil preferido"
            using_preferred = True
        elif "intel2115" in str(inf_path).lower():
            reason = "coincide con carpeta Intel2115 detectada"

        if candidate.version not in {"No detectado", TARGET_VERSION} and "intel" in candidate.provider.lower():
            return False, f"La versión detectada ({candidate.version}) no coincide con la meta {TARGET_VERSION}.", None

        plan = ApplyPlan(
            target_device=state.intel_adapter,
            target_pnp=state.intel_pnp_device_id,
            inf_path=str(inf_path),
            source_reason=reason,
            using_preferred=using_preferred,
        )
        msg = (
            f"Se aplicará {plan.inf_path} sobre {plan.target_device}. "
            f"Motivo de selección: {plan.source_reason}."
        )
        return True, msg, plan

    def apply_driver(self, plan: ApplyPlan, timeout_sec: int = 90) -> tuple[bool, str]:
        if not self.is_windows:
            return False, "La instalación solo está disponible en Windows 11."

        cmd = ["pnputil", "/add-driver", plan.inf_path, "/install"]
        self.log(f"Destino de aplicación: {plan.target_device}")
        self.log(f"INF seleccionado para aplicar: {plan.inf_path}")
        self.log(f"Motivo de selección: {plan.source_reason}")
        self.log(f"Ejecutando: {' '.join(cmd)}")

        start = time.perf_counter()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            elapsed = time.perf_counter() - start
            detail = (
                f"Tiempo de espera agotado ({timeout_sec}s).\n"
                f"Comando: {' '.join(cmd)}\n"
                f"Tiempo consumido: {elapsed:.1f}s\n"
                f"INF: {plan.inf_path}\n"
                f"Dispositivo objetivo: {plan.target_device}\n"
                f"STDOUT: {stdout[:800]}\nSTDERR: {stderr[:800]}"
            )
            self.log(detail)
            return False, detail

        elapsed = time.perf_counter() - start
        if proc.returncode == 0:
            return True, stdout.strip() or f"Controlador aplicado correctamente en {elapsed:.1f}s."

        output = (stdout + "\n" + stderr).strip()
        self.log(f"Error pnputil ({proc.returncode}): {output[:900]}")
        return False, output or "No fue posible aplicar el controlador."

    def refresh_adapter(self, pnp_device_id: str) -> tuple[bool, str]:
        if not self.is_windows:
            return False, "Solo disponible en Windows."
        if not pnp_device_id:
            return False, "No se detectó identificador PNP del adaptador Intel objetivo."

        cmd = ["pnputil", "/restart-device", pnp_device_id]
        self.log(f"Refrescando adaptador Intel: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado al refrescar el adaptador Intel."

        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Adaptador Intel reiniciado."
        return False, (proc.stdout + "\n" + proc.stderr).strip()

    def apply_and_refresh(self, plan: ApplyPlan) -> tuple[bool, str]:
        ok, detail = self.apply_driver(plan)
        if not ok:
            return False, detail
        ok_refresh, refresh_detail = self.refresh_adapter(plan.target_pnp)
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
        return None
