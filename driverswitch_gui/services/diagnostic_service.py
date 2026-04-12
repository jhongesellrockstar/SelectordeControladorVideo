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
        checklist = [
            f"Adaptador virtual detectado: {state.virtual_adapter}",
            f"GPU física Intel detectada: {state.intel_adapter}",
            f"Driver Intel activo: {state.intel_driver_version}",
            f"INF Intel activo: {state.intel_inf_name}",
            f"Perfil coincide: {'Sí' if profile_comparison.matches else 'No'}",
            f"Intel2115 detectado: {'Sí' if intel2115 else 'No'}",
        ]

        if state.intel_driver_version == TARGET:
            return DiagnosticResult(
                ok=True,
                summary="La GPU Intel ya está en la versión objetivo para Meta Quest 3.",
                checklist=checklist,
                next_step="Verifica conexión en Windows App y vuelve a diagnosticar si falla.",
            )

        if intel2115:
            return DiagnosticResult(
                ok=False,
                summary="Intel no está en la versión objetivo, pero se detectó Intel2115\\iigd_dch.inf listo para aplicar.",
                checklist=checklist,
                next_step="Pulsa 'Aplicar controlador Intel objetivo', reinicia y rediagnostica.",
            )

        return DiagnosticResult(
            ok=False,
            summary="Intel no está en la versión objetivo y no se detectó Intel2115 automáticamente.",
            checklist=checklist,
            next_step="Usa 'Agregar carpeta INF' con Intel2115 y repite diagnóstico.",
        )
