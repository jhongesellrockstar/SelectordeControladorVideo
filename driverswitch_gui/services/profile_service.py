from __future__ import annotations

from pathlib import Path

from driverswitch_gui.models import ProfileComparison, ProfileData
from driverswitch_gui.services.system_info import SystemState


class ProfileService:
    def crear_perfil_vacio(self) -> ProfileData:
        profile = ProfileData()
        profile.sections = {
            "PERFIL": {"nombre": "Perfil sin nombre", "descripcion": ""},
            "EQUIPO": {"equipo": "", "gpu": "Intel(R) UHD Graphics"},
            "DRIVER": {"provider": "Intel", "version": "31.0.101.2115", "inf": "iigd_dch.inf", "fecha": ""},
            "RUTAS": {"intel2115": ""},
        }
        return profile

    def cargar_perfil(self, ruta: Path) -> ProfileData:
        profile = ProfileData()
        current_section = "GENERAL"
        profile.sections[current_section] = {}
        for raw_line in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip() or "GENERAL"
                profile.sections.setdefault(current_section, {})
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                profile.sections.setdefault(current_section, {})[key.strip()] = value.strip()
        return profile

    def guardar_perfil(self, ruta: Path, profile: ProfileData) -> None:
        lines: list[str] = []
        for section, values in profile.sections.items():
            lines.append(f"[{section}]")
            for key, value in values.items():
                lines.append(f"{key}={value}")
            lines.append("")
        ruta.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def comparar_perfil_vs_sistema(self, profile: ProfileData, state: SystemState) -> ProfileComparison:
        checks = [
            ("EQUIPO/equipo", profile.get("EQUIPO", "equipo"), state.computer_name),
            ("EQUIPO/gpu", profile.get("EQUIPO", "gpu"), state.intel_adapter),
            ("DRIVER/provider", profile.get("DRIVER", "provider"), state.intel_provider),
            ("DRIVER/version", profile.get("DRIVER", "version"), state.intel_driver_version),
            ("DRIVER/inf", profile.get("DRIVER", "inf"), state.intel_inf_name),
        ]
        details: list[str] = []
        matches = True
        for label, expected, actual in checks:
            if not expected:
                details.append(f"{label}: sin valor en perfil (omitido)")
                continue
            if expected.lower() in (actual or "").lower():
                details.append(f"{label}: coincide ({actual})")
            else:
                details.append(f"{label}: difiere (perfil={expected} / sistema={actual})")
                matches = False
        return ProfileComparison(matches=matches, details=details)
