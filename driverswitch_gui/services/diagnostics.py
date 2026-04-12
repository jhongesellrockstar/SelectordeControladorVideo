from __future__ import annotations

from dataclasses import dataclass

from driverswitch_gui.services.system_info import SystemState


@dataclass(slots=True)
class Quest3Diagnostic:
    verdict: str
    recommendation: str
    risk_oem: bool


class DiagnosticsService:
    target_version = "31.0.101.2115"

    def evaluate(self, state: SystemState, has_intel2115: bool, has_virtual: bool) -> Quest3Diagnostic:
        risk_oem = state.intel_driver_version != self.target_version and has_virtual
        if state.intel_driver_version == self.target_version:
            return Quest3Diagnostic(
                verdict="Compatible",
                recommendation="El driver Intel ya está correcto. Prueba Mixed Reality Link.",
                risk_oem=False,
            )
        if has_intel2115:
            return Quest3Diagnostic(
                verdict="Compatible con riesgo" if risk_oem else "No compatible",
                recommendation="Aplicar Intel2115 y reiniciar. Si persiste ranking OEM, usar ruta avanzada.",
                risk_oem=risk_oem,
            )
        return Quest3Diagnostic(
            verdict="No compatible",
            recommendation="No se encontró Intel2115 en rutas permitidas. Usa 'Agregar carpeta INF'.",
            risk_oem=risk_oem,
        )
