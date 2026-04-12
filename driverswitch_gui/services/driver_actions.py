from __future__ import annotations

import platform
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from driverswitch_gui.models import DriverCandidate
from driverswitch_gui.services.system_info import SystemInfoService, SystemState

TARGET_VERSION = "31.0.101.2115"


@dataclass(slots=True)
class ApplyPlan:
    target_device: str
    target_pnp: str
    inf_path: str
    source_reason: str
    using_preferred: bool


@dataclass(slots=True)
class ApplyResult:
    ok: bool
    message: str
    before_version: str
    after_version: str
    reverted: bool


class DriverActionService:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.is_windows = platform.system().lower() == "windows"
        self.log = log or (lambda _: None)
        self.system_reader = SystemInfoService(log=self.log)

    def validate_candidate(self, candidate: DriverCandidate, state: SystemState, preferred_inf_path: str = "") -> tuple[bool, str, ApplyPlan | None]:
        if not state.is_admin:
            return False, "La aplicación no está en modo administrador.", None
        if not candidate:
            return False, "No hay controlador seleccionado.", None
        if not state.intel_adapter or state.intel_adapter == "No detectado":
            return False, "No se detectó Intel(R) UHD Graphics como dispositivo objetivo.", None

        inf_path = self._resolve_inf_path(candidate)
        if not inf_path:
            return False, "No se pudo resolver la ruta del INF seleccionado.", None

        reason = "selección manual"
        using_preferred = False
        if preferred_inf_path and Path(preferred_inf_path).exists() and Path(preferred_inf_path).resolve() == inf_path.resolve():
            reason = "coincide con perfil preferido"
            using_preferred = True
        elif "intel2115" in str(inf_path).lower():
            reason = "coincide con carpeta Intel2115 detectada"

        plan = ApplyPlan(
            target_device=state.intel_adapter,
            target_pnp=state.intel_pnp_device_id,
            inf_path=str(inf_path),
            source_reason=reason,
            using_preferred=using_preferred,
        )
        return True, f"Se aplicará {plan.inf_path} sobre {plan.target_device}. Motivo: {plan.source_reason}.", plan

    def apply_and_verify(self, plan: ApplyPlan, current_state: SystemState, block_updates: bool = False) -> ApplyResult:
        if block_updates:
            self._set_windows_driver_update_policy(disable=True)

        before_version = current_state.intel_driver_version
        before_inf = current_state.intel_inf_name
        self.log(f"Driver Intel antes de aplicar: {before_version} ({before_inf})")

        add_ok, add_msg, oem_inf = self._add_driver_force(plan)
        if not add_ok:
            return ApplyResult(False, add_msg, before_version, before_version, False)

        inst_id = self._find_intel_instance_id()
        self.log(f"InstanceId usado para update-driver: {inst_id or 'No detectado'}")
        if not inst_id:
            return ApplyResult(False, "No se detectó InstanceId Intel para actualizar dispositivo.", before_version, before_version, False)

        self.log(f"oemXX.inf aplicado: {oem_inf}")
        update_ok, update_msg = self._update_driver_device(oem_inf, inst_id)
        self.log(f"Resultado update-driver: {update_msg[:400]}")
        if not update_ok:
            return ApplyResult(False, update_msg, before_version, before_version, False)

        refresh_ok, refresh_msg = self.refresh_adapter(inst_id)
        self.log(f"Resultado refresco: {refresh_msg}")

        post_state = self.system_reader.get_system_state()
        after_version = post_state.intel_driver_version
        self.log(f"Driver Intel después de aplicar: {after_version} ({post_state.intel_inf_name})")

        reverted = after_version != TARGET_VERSION
        if reverted:
            msg = (
                "Windows mantiene el controlador anterior por política de compatibilidad OEM o ranking de drivers.\n"
                f"Antes: {before_version}\nDespués: {after_version}\n"
                f"Detalle actualización: {update_msg}\nRefresco: {refresh_msg}"
            )
            return ApplyResult(False, msg, before_version, after_version, True)

        msg = f"Driver aplicado correctamente. Antes: {before_version} -> Después: {after_version}."
        return ApplyResult(True, msg, before_version, after_version, False)

    def _add_driver_force(self, plan: ApplyPlan, timeout_sec: int = 120) -> tuple[bool, str, str]:
        cmd = ["pnputil", "/add-driver", plan.inf_path, "/install", "/force"]
        self.log(f"Comando exacto: {' '.join(cmd)}")
        code, stdout, stderr, elapsed, timeout = self._run_process(cmd, timeout_sec)
        self.log(f"Código salida: {code}; tiempo: {elapsed:.1f}s")
        if timeout:
            return False, self._timeout_message(cmd, elapsed, plan, stdout, stderr), ""
        if code != 0:
            return False, (stdout + "\n" + stderr).strip() or "Falló /add-driver /install /force", ""

        combined_output = (stdout + "\n" + stderr)
        oem_inf = self._extract_oem_inf(combined_output) or self._resolve_oem_from_inf(plan.inf_path)
        if not oem_inf:
            return False, "No se pudo determinar oemXX.inf después de agregar el driver.", ""
        self.log(f"OEM INF resultante: {oem_inf}")
        return True, stdout.strip(), oem_inf

    def _update_driver_device(self, oem_inf: str, instance_id: str, timeout_sec: int = 90) -> tuple[bool, str]:
        cmd = ["pnputil", "/update-driver", oem_inf, instance_id]
        self.log(f"Comando exacto: {' '.join(cmd)}")
        code, stdout, stderr, elapsed, timeout = self._run_process(cmd, timeout_sec)
        self.log(f"Código salida update-driver: {code}; tiempo: {elapsed:.1f}s")
        if timeout:
            return False, f"Timeout update-driver ({elapsed:.1f}s).\nSTDOUT: {stdout[:900]}\nSTDERR: {stderr[:900]}"
        if code != 0:
            return False, (stdout + "\n" + stderr).strip() or "Falló update-driver"
        return True, stdout.strip() or "update-driver ejecutado"

    def refresh_adapter(self, pnp_device_id: str) -> tuple[bool, str]:
        if not self.is_windows:
            return False, "Solo disponible en Windows."
        cmd = ["pnputil", "/restart-device", pnp_device_id]
        code, stdout, stderr, _, timeout = self._run_process(cmd, 30)
        if timeout:
            return False, "Timeout refrescando adaptador Intel."
        if code == 0:
            return True, stdout.strip() or "Adaptador Intel reiniciado."
        return False, (stdout + "\n" + stderr).strip()

    def request_reboot(self) -> tuple[bool, str]:
        proc = subprocess.run(["shutdown", "/r", "/t", "5"], capture_output=True, text=True, check=False)
        return (proc.returncode == 0, "Reinicio programado en 5 segundos." if proc.returncode == 0 else proc.stderr.strip() or "No fue posible programar reinicio")

    def _resolve_inf_path(self, candidate: DriverCandidate) -> Path | None:
        if candidate.source_path:
            inf = Path(candidate.source_path)
            return inf if inf.exists() else None
        return None

    def _find_intel_instance_id(self) -> str:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PnpDevice -Class Display | Select-Object FriendlyName,InstanceId,Status | ConvertTo-Json -Depth 4",
        ]
        code, stdout, stderr, _, timeout = self._run_process(cmd, 30)
        if timeout or code != 0:
            self.log(f"No se pudo leer InstanceId con Get-PnpDevice: {(stdout + stderr)[:260]}")
            return ""
        try:
            import json

            data = json.loads(stdout)
            items = data if isinstance(data, list) else [data]
            for item in items:
                name = str((item or {}).get("FriendlyName", "")).lower()
                if "intel" in name and any(k in name for k in ["uhd", "iris", "graphics"]):
                    inst = str((item or {}).get("InstanceId", "")).strip()
                    if inst:
                        self.log(f"InstanceId Intel detectado (Get-PnpDevice): {inst}")
                        return inst
        except Exception as exc:
            self.log(f"Error parseando Get-PnpDevice: {exc}")
        return ""

    @staticmethod
    def _find_field(block: str, keys: list[str]) -> str:
        for line in block.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            key = k.strip().lower()
            if any(target in key for target in keys):
                return v.strip()
        return ""

    @staticmethod
    def _extract_oem_inf(text: str) -> str:
        match = re.search(r"(oem\d+\.inf)", text, re.IGNORECASE)
        return match.group(1) if match else ""

    def _resolve_oem_from_inf(self, inf_path: str) -> str:
        name = Path(inf_path).name.lower()
        cmd = ["pnputil", "/enum-drivers", "/class", "Display"]
        code, stdout, _, _, _ = self._run_process(cmd, 30)
        if code != 0:
            return ""
        blocks = re.split(r"\r?\n\s*\r?\n", stdout)
        for block in blocks:
            if name not in block.lower():
                continue
            pub = self._find_field(block, ["published name", "nombre publicado"])
            if pub.lower().endswith(".inf"):
                return pub
        return ""

    def _set_windows_driver_update_policy(self, disable: bool) -> None:
        value = "0" if disable else "1"
        cmd = [
            "reg",
            "add",
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching",
            "/v",
            "SearchOrderConfig",
            "/t",
            "REG_DWORD",
            "/d",
            value,
            "/f",
        ]
        code, stdout, stderr, _, _ = self._run_process(cmd, 20)
        self.log(f"Política Windows Update drivers ({'bloquear' if disable else 'restaurar'}): código {code}")
        if code != 0:
            self.log(f"No se pudo ajustar política: {(stdout + stderr)[:300]}")

    def _run_process(self, cmd: list[str], timeout_sec: int) -> tuple[int, str, str, float, bool]:
        start = time.perf_counter()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
            return proc.returncode, stdout, stderr, time.perf_counter() - start, False
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return -1, stdout, stderr, time.perf_counter() - start, True

    @staticmethod
    def _timeout_message(cmd: list[str], elapsed: float, plan: ApplyPlan, stdout: str, stderr: str) -> str:
        return (
            f"Tiempo de espera agotado.\nComando ejecutado: {' '.join(cmd)}\n"
            f"Tiempo consumido: {elapsed:.1f}s\nINF: {plan.inf_path}\n"
            f"Dispositivo objetivo: {plan.target_device}\nSTDOUT: {stdout[:900]}\nSTDERR: {stderr[:900]}"
        )
