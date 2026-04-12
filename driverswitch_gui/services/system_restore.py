from __future__ import annotations

from typing import Callable


class SystemRestoreService:
    """Arquitectura preparada: creación de restore point puede requerir políticas/servicios habilitados."""

    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.log = log or (lambda _: None)

    def create_restore_point(self, description: str = "DriverSwitch Quest3 Repair") -> tuple[bool, str]:
        self.log("System Restore: función preparada, no automatizada en esta versión por compatibilidad OEM/políticas.")
        return False, "No automatizado en esta versión. Cree un punto de restauración manual antes de cambios avanzados."
