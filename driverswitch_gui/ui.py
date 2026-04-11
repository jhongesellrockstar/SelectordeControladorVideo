from __future__ import annotations

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from driverswitch_gui.models import DriverCandidate
from driverswitch_gui.services.audit_logger import build_logger
from driverswitch_gui.services.config_store import ConfigStore, UserConfig
from driverswitch_gui.services.driver_actions import DriverActionService
from driverswitch_gui.services.driver_inventory import DriverInventoryService
from driverswitch_gui.services.system_info import SystemInfoService, SystemState


class DriverSwitchApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DriverSwitch GUI - Selector de controlador de video")
        self.geometry("1100x650")

        self.logger = build_logger()
        self.config_store = ConfigStore()
        self.system_service = SystemInfoService()
        self.inventory_service = DriverInventoryService()
        self.action_service = DriverActionService()

        self.user_config = self.config_store.load()
        self.state = SystemState("", "", "", "", "", "", "")
        self.candidates: list[DriverCandidate] = []

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        self.lbl_system = ttk.Label(top, text="Equipo: -")
        self.lbl_system.grid(row=0, column=0, sticky="w", padx=6)

        self.lbl_adapter = ttk.Label(top, text="Adaptador activo: -")
        self.lbl_adapter.grid(row=0, column=1, sticky="w", padx=6)

        self.lbl_version = ttk.Label(top, text="Versión activa: -")
        self.lbl_version.grid(row=0, column=2, sticky="w", padx=6)

        self.lbl_inf = ttk.Label(top, text="INF activo: -")
        self.lbl_inf.grid(row=1, column=0, sticky="w", padx=6, pady=(4, 0))

        self.lbl_provider = ttk.Label(top, text="Fabricante: -")
        self.lbl_provider.grid(row=1, column=1, sticky="w", padx=6, pady=(4, 0))

        self.lbl_preferred = ttk.Label(top, text="Preferido: -")
        self.lbl_preferred.grid(row=1, column=2, sticky="w", padx=6, pady=(4, 0))

        middle = ttk.Frame(self)
        middle.pack(fill="both", expand=True, padx=10, pady=8)

        columns = ("origen", "proveedor", "version", "fecha", "inf", "estado", "preferido")
        self.tree = ttk.Treeview(middle, columns=columns, show="headings", height=18)
        headers = {
            "origen": "Origen",
            "proveedor": "Proveedor",
            "version": "Versión",
            "fecha": "Fecha",
            "inf": "INF",
            "estado": "Estado",
            "preferido": "Preferido",
        }
        for key, title in headers.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=140 if key != "inf" else 220, anchor="w")

        scrollbar = ttk.Scrollbar(middle, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(bottom, text="Refrescar estado", command=self.refresh_all).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(bottom, text="Agregar carpeta INF", command=self.add_external_folder).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(bottom, text="Marcar como preferido", command=self.mark_preferred).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(bottom, text="Aplicar controlador", command=self.apply_selected).grid(row=0, column=3, padx=4, pady=4)
        ttk.Button(bottom, text="Refrescar adaptador", command=self.refresh_adapter).grid(row=0, column=4, padx=4, pady=4)
        ttk.Button(bottom, text="Abrir carpeta", command=self.open_folder).grid(row=0, column=5, padx=4, pady=4)
        ttk.Button(bottom, text="Modo recuperación", command=self.quick_recovery).grid(row=0, column=6, padx=4, pady=4)
        ttk.Button(bottom, text="Exportar registro", command=self.export_log).grid(row=0, column=7, padx=4, pady=4)
        ttk.Button(bottom, text="Reiniciar equipo", command=self.reboot).grid(row=0, column=8, padx=4, pady=4)

        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def refresh_all(self) -> None:
        self.state = self.system_service.get_system_state()
        self.lbl_system.config(text=f"Equipo: {self.state.computer_name}")
        self.lbl_adapter.config(text=f"Adaptador activo: {self.state.active_adapter}")
        self.lbl_version.config(text=f"Versión activa: {self.state.driver_version} ({self.state.driver_date})")
        self.lbl_inf.config(text=f"INF activo: {self.state.inf_name}")
        self.lbl_provider.config(text=f"Fabricante: {self.state.provider}")

        candidates = self.inventory_service.list_driver_store(active_inf=self.state.inf_name)
        for path in self.user_config.normalized_paths():
            candidates.extend(self.inventory_service.scan_external_folder(Path(path)))

        self.candidates = candidates
        self._render_table()
        self._render_preferred()
        self._set_status("Estado actualizado")

    def _render_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)

        preferred_match = (self.user_config.preferred_inf, self.user_config.preferred_version)
        for idx, candidate in enumerate(self.candidates):
            preferred = "Sí" if (candidate.inf_name, candidate.version) == preferred_match else "No"
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    candidate.source_type,
                    candidate.provider,
                    candidate.version,
                    candidate.driver_date,
                    candidate.inf_name,
                    candidate.status,
                    preferred,
                ),
            )

    def _render_preferred(self) -> None:
        if self.user_config.preferred_inf:
            txt = f"{self.user_config.preferred_inf} ({self.user_config.preferred_version})"
        else:
            txt = "No configurado"
        self.lbl_preferred.config(text=f"Preferido: {txt}")

    def _selected_candidate(self) -> DriverCandidate | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return self.candidates[int(selected[0])]

    def add_external_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona carpeta con INF exportados")
        if not folder:
            return

        detected = self.inventory_service.scan_external_folder(Path(folder))
        if not detected:
            messagebox.showwarning("Carpeta inválida", "No se encontraron controladores de pantalla compatibles.")
            return

        paths = set(self.user_config.normalized_paths())
        paths.add(folder)
        self.user_config.external_paths = sorted(paths)
        self.config_store.save(self.user_config)
        self.logger.info("Carpeta externa añadida: %s", folder)
        self.refresh_all()

    def mark_preferred(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            messagebox.showinfo("Sin selección", "Selecciona una versión en la tabla.")
            return

        self.user_config.preferred_inf = candidate.inf_name
        self.user_config.preferred_version = candidate.version
        self.config_store.save(self.user_config)
        self.logger.info("Controlador preferido: %s %s", candidate.inf_name, candidate.version)
        self.refresh_all()

    def apply_selected(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            messagebox.showinfo("Sin selección", "Selecciona una versión en la tabla.")
            return

        if messagebox.askyesno(
            "Confirmar cambio",
            "Aplicar un controlador puede requerir permisos de administrador y reinicio. ¿Deseas continuar?",
        ):
            ok, detail = self.action_service.apply_driver(candidate)
            if ok:
                messagebox.showinfo("Éxito", detail)
                self.logger.info("Controlador aplicado: %s | %s", candidate.inf_name, detail)
                self.refresh_all()
            else:
                messagebox.showwarning("No se pudo aplicar", detail)
                self.logger.warning("Fallo al aplicar controlador %s: %s", candidate.inf_name, detail)
            self._set_status(detail)

    def refresh_adapter(self) -> None:
        ok, detail = self.action_service.refresh_adapter(self.state.pnp_device_id)
        if ok:
            messagebox.showinfo("Adaptador", detail)
            self.logger.info("Adaptador refrescado: %s", detail)
        else:
            messagebox.showwarning("Adaptador", detail)
            self.logger.warning("No se pudo refrescar adaptador: %s", detail)
        self._set_status(detail)

    def open_folder(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            return
        folder = candidate.folder_hint
        if not folder:
            messagebox.showinfo("Sin carpeta", "Este elemento no tiene ruta local asociada.")
            return

        if os.name == "nt":
            os.startfile(str(folder))
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)

    def quick_recovery(self) -> None:
        if not self.user_config.preferred_inf:
            messagebox.showinfo("Recuperación", "No existe controlador preferido guardado.")
            return

        candidate = next(
            (
                c
                for c in self.candidates
                if c.inf_name == self.user_config.preferred_inf and c.version == self.user_config.preferred_version
            ),
            None,
        )
        if not candidate:
            messagebox.showwarning("Recuperación", "El controlador preferido no está disponible en el inventario actual.")
            return

        ok, detail = self.action_service.apply_driver(candidate)
        if ok:
            messagebox.showinfo("Recuperación", "Se aplicó el controlador preferido correctamente.")
            self.logger.info("Recuperación rápida ejecutada: %s", candidate.inf_name)
            self.refresh_all()
        else:
            messagebox.showwarning("Recuperación", detail)
            self.logger.warning("Recuperación rápida fallida: %s", detail)
        self._set_status(detail)

    def export_log(self) -> None:
        output = filedialog.asksaveasfilename(
            title="Guardar log",
            defaultextension=".log",
            filetypes=[("Log", "*.log"), ("Texto", "*.txt")],
        )
        if not output:
            return

        logfile = self.config_store.root / "driverswitch.log"
        if not logfile.exists():
            messagebox.showwarning("Exportar", "No hay registros aún.")
            return

        Path(output).write_text(logfile.read_text(encoding="utf-8"), encoding="utf-8")
        messagebox.showinfo("Exportar", "Registro exportado correctamente.")
        self._set_status(f"Log exportado a {output}")

    def reboot(self) -> None:
        if not messagebox.askyesno("Reiniciar", "¿Deseas reiniciar el equipo en 5 segundos?"):
            return
        ok, detail = self.action_service.request_reboot()
        if ok:
            self.logger.info(detail)
        else:
            self.logger.warning(detail)
        self._set_status(detail)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)


if __name__ == "__main__":
    app = DriverSwitchApp()
    app.mainloop()
