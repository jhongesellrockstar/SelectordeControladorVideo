from __future__ import annotations

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from driverswitch_gui.models import DriverCandidate, ProfileData
from driverswitch_gui.services.audit_logger import build_logger
from driverswitch_gui.services.config_store import ConfigStore
from driverswitch_gui.services.driver_actions import DriverActionService
from driverswitch_gui.services.driver_inventory import DriverInventoryService
from driverswitch_gui.services.profile_service import ProfileService
from driverswitch_gui.services.system_info import SystemInfoService, SystemState

MIXED_REALITY_TARGET = "31.0.101.2115"


class DriverSwitchApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DriverSwitch GUI - Selector de controlador de video")
        self.geometry("1250x700")

        self.logger = build_logger()
        self.config_store = ConfigStore()
        self.system_service = SystemInfoService()
        self.inventory_service = DriverInventoryService()
        self.action_service = DriverActionService()
        self.profile_service = ProfileService()

        self.user_config = self.config_store.load()
        self.state = SystemState("", "", "", "", "", "", "")
        self.candidates: list[DriverCandidate] = []
        self.profile_path = self.config_store.root / "perfil_base.txt"
        self.profile = self._load_default_profile()

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        self.lbl_system = ttk.Label(top, text="Equipo: -")
        self.lbl_system.grid(row=0, column=0, sticky="w", padx=6)
        self.lbl_adapter = ttk.Label(top, text="GPU activa: -")
        self.lbl_adapter.grid(row=0, column=1, sticky="w", padx=6)
        self.lbl_version = ttk.Label(top, text="Driver activo: -")
        self.lbl_version.grid(row=0, column=2, sticky="w", padx=6)

        self.lbl_inf = ttk.Label(top, text="INF activo: -")
        self.lbl_inf.grid(row=1, column=0, sticky="w", padx=6)
        self.lbl_provider = ttk.Label(top, text="Fabricante: -")
        self.lbl_provider.grid(row=1, column=1, sticky="w", padx=6)
        self.lbl_profile_state = ttk.Label(top, text="Estado vs perfil: -")
        self.lbl_profile_state.grid(row=1, column=2, sticky="w", padx=6)

        self.lbl_mr = ttk.Label(top, text="Compatibilidad RM: -")
        self.lbl_mr.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=(2, 0))

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
            width = 160 if key not in {"inf", "estado"} else 260
            self.tree.column(key, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(middle, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))
        buttons = [
            ("Refrescar estado", self.refresh_all),
            ("Agregar carpeta INF", self.add_external_folder),
            ("Marcar como preferido", self.mark_preferred),
            ("Aplicar controlador", self.apply_selected),
            ("Refrescar adaptador", self.refresh_adapter),
            ("Abrir carpeta", self.open_folder),
            ("Modo recuperación", self.quick_recovery),
            ("Exportar registro", self.export_log),
            ("Reiniciar equipo", self.reboot),
            ("Cargar perfil", self.load_profile),
            ("Guardar perfil", self.save_profile),
            ("Nuevo perfil", self.new_profile),
            ("Comparar perfil vs sistema", self.compare_profile),
        ]
        for col, (text, command) in enumerate(buttons):
            ttk.Button(bottom, text=text, command=command).grid(row=0, column=col, padx=3, pady=4)

        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def _load_default_profile(self) -> ProfileData:
        if self.profile_path.exists():
            try:
                return self.profile_service.cargar_perfil(self.profile_path)
            except OSError:
                pass
        profile = self.profile_service.crear_perfil_vacio()
        self.profile_service.guardar_perfil(self.profile_path, profile)
        return profile

    def refresh_all(self) -> None:
        self.state = self.system_service.get_system_state()
        self.lbl_system.config(text=f"Equipo detectado: {self.state.computer_name}")
        self.lbl_adapter.config(text=f"GPU activa: {self.state.active_adapter}")
        self.lbl_version.config(text=f"Driver activo: {self.state.driver_version} ({self.state.driver_date})")
        self.lbl_inf.config(text=f"INF activo: {self.state.inf_name}")
        self.lbl_provider.config(text=f"Proveedor: {self.state.provider}")

        candidates = self.inventory_service.list_driver_store(active_inf=self.state.inf_name)
        for path in self.user_config.normalized_paths():
            candidates.extend(self.inventory_service.scan_external_folder(Path(path)))

        intel_candidate = self.inventory_service.autodetect_intel2115([Path.cwd(), Path.home()])
        if intel_candidate and all(c.source_path != intel_candidate.source_path for c in candidates):
            candidates.append(intel_candidate)
            if not self.user_config.preferred_inf:
                self.user_config.preferred_inf = intel_candidate.inf_name
                self.user_config.preferred_version = intel_candidate.version
                self.config_store.save(self.user_config)

        self.candidates = candidates
        self._render_table()
        self._render_profile_status()
        self._render_mixed_reality_warning()
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

    def _render_profile_status(self) -> None:
        comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, self.state)
        text = "coincide" if comparison.matches else "difiere"
        self.lbl_profile_state.config(text=f"Estado vs perfil: {text}")

    def _render_mixed_reality_warning(self) -> None:
        if self.state.driver_version != MIXED_REALITY_TARGET:
            self.lbl_mr.config(
                text=(
                    f"Compatibilidad RM: Advertencia. Versión activa {self.state.driver_version}; "
                    f"se recomienda {MIXED_REALITY_TARGET} para Meta Quest 3."
                )
            )
        else:
            self.lbl_mr.config(text="Compatibilidad RM: correcta")

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
        valid, validation_msg = self.action_service.validate_candidate(candidate, self.state)
        if not valid:
            messagebox.showwarning("Compatibilidad", validation_msg)
            return
        if not messagebox.askyesno("Confirmar cambio", f"{validation_msg}\n\n¿Deseas continuar?"):
            return
        ok, detail = self.action_service.apply_and_refresh(candidate, self.state.pnp_device_id)
        if ok:
            messagebox.showinfo("Resultado", detail)
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
        ok, detail = self.action_service.apply_and_refresh(candidate, self.state.pnp_device_id)
        if ok:
            messagebox.showinfo("Recuperación", "Se restauró el controlador preferido.")
            self.logger.info("Recuperación rápida ejecutada: %s", candidate.inf_name)
            self.refresh_all()
        else:
            messagebox.showwarning("Recuperación", detail)
            self.logger.warning("Recuperación rápida fallida: %s", detail)
        self._set_status(detail)

    def export_log(self) -> None:
        output = filedialog.asksaveasfilename(
            title="Guardar log",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Log", "*.log")],
        )
        if not output:
            return
        logfile = self.config_store.root / "driverswitch.log"
        if not logfile.exists():
            messagebox.showwarning("Exportar", "No hay registros aún.")
            return
        Path(output).write_text(logfile.read_text(encoding="utf-8"), encoding="utf-8")
        messagebox.showinfo("Exportar", "Registro exportado correctamente.")

    def reboot(self) -> None:
        if not messagebox.askyesno("Reiniciar", "¿Deseas reiniciar el equipo en 5 segundos?"):
            return
        ok, detail = self.action_service.request_reboot()
        self.logger.info(detail if ok else f"Reinicio fallido: {detail}")
        self._set_status(detail)

    def load_profile(self) -> None:
        path = filedialog.askopenfilename(title="Cargar perfil", filetypes=[("Perfil txt", "*.txt"), ("Todos", "*.*")])
        if not path:
            return
        self.profile = self.profile_service.cargar_perfil(Path(path))
        self.profile_path = Path(path)
        self.logger.info("Perfil cargado: %s", path)
        self.compare_profile()

    def save_profile(self) -> None:
        if not self.profile.sections:
            self.profile = self.profile_service.crear_perfil_vacio()
        self.profile.set("EQUIPO", "equipo", self.state.computer_name)
        self.profile.set("EQUIPO", "gpu", self.state.active_adapter)
        self.profile.set("DRIVER", "provider", self.state.provider)
        self.profile.set("DRIVER", "version", self.state.driver_version)
        self.profile.set("DRIVER", "inf", self.state.inf_name)
        self.profile.set("DRIVER", "fecha", self.state.driver_date)

        target = filedialog.asksaveasfilename(
            title="Guardar perfil",
            initialfile=self.profile_path.name,
            defaultextension=".txt",
            filetypes=[("Perfil txt", "*.txt")],
        )
        if not target:
            return
        self.profile_service.guardar_perfil(Path(target), self.profile)
        self.profile_path = Path(target)
        self.logger.info("Perfil guardado: %s", target)
        self._set_status(f"Perfil guardado: {target}")

    def new_profile(self) -> None:
        self.profile = self.profile_service.crear_perfil_vacio()
        messagebox.showinfo("Perfil", "Se creó un perfil vacío en memoria. Usa 'Guardar perfil' para persistirlo.")

    def compare_profile(self) -> None:
        comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, self.state)
        self.lbl_profile_state.config(text=f"Estado vs perfil: {'coincide' if comparison.matches else 'difiere'}")
        messagebox.showinfo("Comparación", "\n".join(comparison.details))

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)


if __name__ == "__main__":
    app = DriverSwitchApp()
    app.mainloop()
