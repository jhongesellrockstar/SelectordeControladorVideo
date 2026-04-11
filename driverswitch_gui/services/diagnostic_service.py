from __future__ import annotations

from dataclasses import dataclass

from driverswitch_gui.models import DriverCandidate, ProfileComparison
from driverswitch_gui.services.system_info import SystemState

TARGET = "31.0.101.2115"


@dataclass(slots=True)
class DiagnosticResult:
    ok: bool
    summary: str
    checklist: list[str]
    next_step: str


class DiagnosticService:
    def run(
        self,
        state: SystemState,
        profile_comparison: ProfileComparison,
        intel2115: DriverCandidate | None,
    ) -> DiagnosticResult:
        checklist: list[str] = []
        checklist.append(f"GPU principal: {state.active_adapter}")
        checklist.append(f"Driver activo: {state.driver_version}")
        checklist.append(f"INF activo: {state.inf_name}")
        checklist.append(f"Perfil coincide: {'Sí' if profile_comparison.matches else 'No'}")
        checklist.append(f"Intel2115 detectado: {'Sí' if intel2115 else 'No'}")

        version_ok = state.driver_version == TARGET
        if version_ok:
            checklist.append("Meta Quest 3: versión objetivo detectada.")
            return DiagnosticResult(
                ok=True,
                summary="El driver objetivo para Meta Quest 3 ya está activo.",
                checklist=checklist,
                next_step="Abre Windows App/Vínculo de realidad mixta y verifica conexión.",
            )

        if intel2115:
            return DiagnosticResult(
                ok=False,
                summary=(
                    "Tu controlador actual no coincide con 31.0.101.2115, pero se detectó iigd_dch.inf de Intel2115."
                ),
                checklist=checklist,
                next_step="Selecciona la fila Intel2115 y pulsa 'Aplicar controlador'. Luego reinicia y vuelve a diagnosticar.",
            )

        return DiagnosticResult(
            ok=False,
            summary="El controlador activo no coincide con el objetivo y no se encontró Intel2115 automáticamente.",
            checklist=checklist,
            next_step="Pulsa 'Agregar carpeta INF', selecciona la carpeta Intel2115, aplica el driver y reinicia.",
        )
