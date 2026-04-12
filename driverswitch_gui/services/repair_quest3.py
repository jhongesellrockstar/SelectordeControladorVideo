from __future__ import annotations

import json
from typing import Callable

from driverswitch_gui.services.subprocess_utils import run_hidden


class RepairQuest3Service:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.log = log or (lambda _: None)

    def disable_virtual_displays(self) -> tuple[bool, str]:
        return self._toggle_virtual_displays(enable=False)

    def restore_virtual_displays(self) -> tuple[bool, str]:
        return self._toggle_virtual_displays(enable=True)

    def _toggle_virtual_displays(self, enable: bool) -> tuple[bool, str]:
        ps = (
            "Get-PnpDevice -Class Display | "
            "Where-Object {$_.FriendlyName -match 'Meta Virtual Monitor|MrIdd'} | "
            "Select-Object FriendlyName,InstanceId | ConvertTo-Json -Depth 4"
        )
        proc = run_hidden(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
        if proc.returncode != 0 or not proc.stdout.strip():
            return False, "No se detectaron virtual displays Meta/MrIdd para modificar."

        data = json.loads(proc.stdout)
        rows = data if isinstance(data, list) else [data]
        cmd_name = "/enable-device" if enable else "/disable-device"
        changed = 0
        for row in rows:
            inst = (row or {}).get("InstanceId", "")
            if not inst:
                continue
            proc2 = run_hidden(["pnputil", cmd_name, inst], capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
            self.log(f"{cmd_name} {inst} => rc={proc2.returncode}")
            if proc2.returncode == 0:
                changed += 1
        if changed == 0:
            return False, "No se pudo modificar ningún virtual display."
        return True, f"Virtual displays {'restaurados' if enable else 'deshabilitados'}: {changed}"
