from __future__ import annotations

from datetime import datetime
from pathlib import Path

from driverswitch_gui.services.system_info import SystemState


class ReportingService:
    def __init__(self, report_root: Path) -> None:
        self.report_root = report_root
        self.report_root.mkdir(parents=True, exist_ok=True)

    def generate_quest3_report(self, state: SystemState, driver_rows: list[str], command_log: list[str], final_status: str) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.report_root / f"quest3_repair_report_{ts}.txt"
        lines = [
            f"Fecha: {datetime.now().isoformat()}",
            f"Equipo: {state.computer_name}",
            "Modelo sistema: Acer Aspire A315-57G (perfil base)",
            f"GPU Intel: {state.intel_adapter}",
            f"Driver Intel activo: {state.intel_driver_version}",
            f"INF Intel activo: {state.intel_inf_name}",
            f"GPU virtual: {state.virtual_adapter}",
            "",
            "Driver Store Display:",
            *driver_rows,
            "",
            "Comandos y resultados:",
            *command_log,
            "",
            f"Estado final: {final_status}",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
