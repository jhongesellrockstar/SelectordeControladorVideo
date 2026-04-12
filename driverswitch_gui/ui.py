from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from driverswitch_gui.models import DriverCandidate, ProfileComparison, ProfileData
from driverswitch_gui.services.audit_logger import build_logger, technical_log_path
from driverswitch_gui.services.config_store import ConfigStore
from driverswitch_gui.services.diagnostic_service import DiagnosticResult, DiagnosticService
from driverswitch_gui.services.driver_actions import ApplyPlan, DriverActionService
from driverswitch_gui.services.driver_inventory import DriverInventoryService
from driverswitch_gui.services.profile_service import ProfileService
from driverswitch_gui.services.system_info import SystemInfoService, SystemState

MIXED_REALITY_TARGET = "31.0.101.2115"


class DriverSwitchApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DriverSwitch GUI - Selector de controlador de video")
        self.geometry("1450x860")

        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.logger = build_logger()
        self.config_store = ConfigStore()
        self.user_config = self.config_store.load()

        self.state = SystemState("-", "-", "-", "-", "-", "-", "", "-", "-", "-", "-", "", "-", False)
        self.profile: ProfileData = ProfileData()
        self.profile_comparison = ProfileComparison(matches=False, details=["Sin comparar"])
        self.candidates: list[DriverCandidate] = []
        self.intel_candidate: DriverCandidate | None = None
        self.profile_path = self.config_store.root / "perfil_base.txt"

        self.system_service = SystemInfoService(log=self.log_human)
        self.inventory_service = DriverInventoryService(log=self.log_human)
        self.action_service = DriverActionService(log=self.log_human)
        self.profile_service = ProfileService()
        self.diagnostic_service = DiagnosticService()

        self._build_ui()
        self.after(100, self._drain_log_queue)
        self.after(120, self.startup_load)

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=6)
        self.lbl_system = ttk.Label(top, text="Equipo: cargando...")
        self.lbl_system.grid(row=0, column=0, sticky="w", padx=4)
        self.lbl_admin = ttk.Label(top, text="Admin: verificando...")
        self.lbl_admin.grid(row=0, column=1, sticky="w", padx=4)
        self.lbl_virtual = ttk.Label(top, text="Adaptador virtual: cargando...")
        self.lbl_virtual.grid(row=0, column=2, sticky="w", padx=4)

        self.lbl_intel = ttk.Label(top, text="GPU Intel objetivo: cargando...")
        self.lbl_intel.grid(row=1, column=0, sticky="w", padx=4)
        self.lbl_intel_driver = ttk.Label(top, text="Driver Intel activo: cargando...")
        self.lbl_intel_driver.grid(row=1, column=1, sticky="w", padx=4)
        self.lbl_intel_inf = ttk.Label(top, text="INF Intel activo: cargando...")
        self.lbl_intel_inf.grid(row=1, column=2, sticky="w", padx=4)

        self.lbl_profile_state = ttk.Label(top, text="Estado vs perfil: pendiente")
        self.lbl_profile_state.grid(row=2, column=0, sticky="w", padx=4)
        self.lbl_mr = ttk.Label(top, text="Compatibilidad RM: pendiente")
        self.lbl_mr.grid(row=2, column=1, columnspan=2, sticky="w", padx=4)

        self.assistant_text = tk.StringVar(value="Resolver mi caso real: iniciando diagnóstico...")
        ttk.Label(self, textvariable=self.assistant_text, background="#f3f7ff", anchor="w").pack(fill="x", padx=10, pady=(2, 8))

        center = ttk.Panedwindow(self, orient="vertical")
        center.pack(fill="both", expand=True, padx=10, pady=4)

        table_frame = ttk.Frame(center)
        center.add(table_frame, weight=3)
        cols = ("origen", "proveedor", "version", "fecha", "inf", "estado", "preferido")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16)
        for key, title in {"origen": "Origen", "proveedor": "Proveedor", "version": "Versión", "fecha": "Fecha", "inf": "INF", "estado": "Estado", "preferido": "Preferido"}.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=170 if key != "estado" else 260, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        tabs = ttk.Notebook(center)
        center.add(tabs, weight=2)
        log_frame = ttk.Frame(tabs)
        tabs.add(log_frame, text="Log en tiempo real")
        self.log_widget = tk.Text(log_frame, state="disabled", bg="#10161f", fg="#d3f0ff", wrap="word")
        self.log_widget.pack(fill="both", expand=True)

        help_frame = ttk.Frame(tabs)
        tabs.add(help_frame, text="Resolver mi caso real")
        help_text = tk.Text(help_frame, wrap="word")
        help_text.insert(
            "1.0",
            "Flujo mínimo recomendado:\n"
            "1) Verifica que 'Admin: Sí'. Si no, pulsa 'Reabrir como administrador'.\n"
            "2) Pulsa 'Diagnosticar mi equipo'.\n"
            "3) Si no coincide con 31.0.101.2115, usa Intel2115\\iigd_dch.inf.\n"
            "4) Pulsa 'Aplicar controlador Intel objetivo'.\n"
            "5) Reinicia y vuelve a diagnosticar.\n"
        )
        help_text.configure(state="disabled")
        help_text.pack(fill="both", expand=True)

        self.block_updates_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="Bloquear actualización automática de drivers (opcional)", variable=self.block_updates_var).pack(anchor="w", padx=12, pady=(0,4))

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=5)
        buttons = [
            ("Resolver mi caso real", self.resolve_real_case),
            ("Diagnosticar mi equipo", self.run_diagnostic),
            ("Refrescar estado", self.refresh_all_async),
            ("Agregar carpeta INF", self.add_external_folder),
            ("Aplicar controlador Intel objetivo", self.apply_selected),
            ("Reabrir como administrador", self.reopen_as_admin),
            ("Exportar log técnico", self.export_technical_log),
            ("Reiniciar equipo", self.reboot),
            ("Cargar perfil", self.load_profile),
            ("Guardar perfil", self.save_profile),
            ("Comparar perfil vs sistema", self.compare_profile),
        ]
        for i, (label, fn) in enumerate(buttons):
            ttk.Button(actions, text=label, command=fn).grid(row=0, column=i, padx=2, pady=2)

        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def log_human(self, message: str) -> None:
        self.log_queue.put(("INFO", message))
        self.logger.info(message)

    def log_error(self, message: str) -> None:
        self.log_queue.put(("ERROR", message))
        self.logger.error(message)

    def _drain_log_queue(self) -> None:
        while True:
            try:
                level, msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", f"[{ts}] {msg}\n")
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")
            if level == "ERROR":
                self.status_var.set(msg)
        self.after(120, self._drain_log_queue)

    def _run_bg(self, label: str, target) -> None:
        def runner() -> None:
            self.log_human(f"Tarea iniciada: {label}")
            t0 = time.perf_counter()
            try:
                target()
            except Exception as exc:
                self.log_error(f"Error en tarea {label}: {exc}")
            self.log_human(f"Tarea finalizada: {label} ({time.perf_counter()-t0:.2f}s)")

        threading.Thread(target=runner, daemon=True).start()

    def startup_load(self) -> None:
        self.log_human("Inicio de aplicación. Cargando perfil base y estado en segundo plano...")
        self.profile = self._load_default_profile()
        self.refresh_all_async()

    def _load_default_profile(self) -> ProfileData:
        if self.profile_path.exists():
            try:
                self.log_human(f"Cargando perfil: {self.profile_path}")
                return self.profile_service.cargar_perfil(self.profile_path)
            except OSError as exc:
                self.log_error(f"No se pudo cargar perfil: {exc}")
        profile = self.profile_service.crear_perfil_vacio()
        self.profile_service.guardar_perfil(self.profile_path, profile)
        return profile

    def refresh_all_async(self) -> None:
        self._run_bg("Actualizar estado", self._refresh_worker)

    def _refresh_worker(self) -> None:
        state = self.system_service.get_system_state()
        candidates = self.inventory_service.list_driver_store(active_inf=state.intel_inf_name)
        for path in self.user_config.normalized_paths():
            candidates.extend(self.inventory_service.scan_external_folder(Path(path)))
        intel = self.inventory_service.autodetect_intel2115([Path(p) for p in self.user_config.normalized_paths()] + [Path.cwd(), Path.home()])
        if intel and all(c.source_path != intel.source_path for c in candidates):
            candidates.append(intel)

        comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, state)
        self.after(0, lambda: self._apply_refresh(state, candidates, intel, comparison))

    def _apply_refresh(self, state: SystemState, candidates: list[DriverCandidate], intel: DriverCandidate | None, comparison: ProfileComparison) -> None:
        self.state, self.candidates, self.intel_candidate, self.profile_comparison = state, candidates, intel, comparison
        self.lbl_system.config(text=f"Equipo: {state.computer_name}")
        self.lbl_admin.config(text=f"Admin: {'Sí' if state.is_admin else 'No'}", foreground="#116611" if state.is_admin else "#aa2200")
        self.lbl_virtual.config(text=f"Adaptador virtual: {state.virtual_adapter}")
        self.lbl_intel.config(text=f"GPU Intel objetivo: {state.intel_adapter}")
        self.lbl_intel_driver.config(text=f"Driver Intel activo: {state.intel_driver_version}")
        self.lbl_intel_inf.config(text=f"INF Intel activo: {state.intel_inf_name}")
        self.lbl_profile_state.config(text=f"Estado vs perfil: {'coincide' if comparison.matches else 'difiere'}")
        rm_ok = state.intel_driver_version == MIXED_REALITY_TARGET
        self.lbl_mr.config(text=("Compatibilidad RM: correcta" if rm_ok else f"Compatibilidad RM: se recomienda {MIXED_REALITY_TARGET}"), foreground="#116611" if rm_ok else "#a14b00")
        self._render_table()
        self._update_assistant()
        self.status_var.set("Estado actualizado")

    def _render_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        preferred_path = self.profile.get("RUTAS", "intel2115", "")
        for idx, c in enumerate(self.candidates):
            preferred = "Sí" if preferred_path and c.source_path and Path(c.source_path) == Path(preferred_path) else "No"
            self.tree.insert("", "end", iid=str(idx), values=(c.source_type, c.provider, c.version, c.driver_date, c.inf_name, c.status, preferred))

    def _update_assistant(self) -> None:
        if not self.state.is_admin:
            msg = "La app no está en administrador. Siguiente paso: pulsa 'Reabrir como administrador'."
        elif self.state.intel_driver_version == MIXED_REALITY_TARGET:
            msg = "Intel ya está en 31.0.101.2115. Siguiente paso: prueba conexión de Meta Quest 3 y rediagnostica."
        elif self.intel_candidate:
            msg = f"Se detectó Intel2115: {self.intel_candidate.source_path}. Siguiente paso: aplicar controlador Intel objetivo."
        else:
            msg = "No se detectó Intel2115. Siguiente paso: agregar carpeta INF correcta y reintentar."
        self.assistant_text.set(f"Resolver mi caso real: {msg}")

    def _selected_candidate(self) -> DriverCandidate | None:
        sel = self.tree.selection()
        return self.candidates[int(sel[0])] if sel else self.intel_candidate

    def _preferred_inf_path(self) -> str:
        return self.profile.get("RUTAS", "intel2115", "")

    def add_external_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona carpeta con INF")
        if not folder:
            return
        paths = set(self.user_config.normalized_paths())
        paths.add(folder)
        self.user_config.external_paths = sorted(paths)
        self.config_store.save(self.user_config)
        self.log_human(f"Carpeta INF agregada: {folder}")
        self.refresh_all_async()

    def apply_selected(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            messagebox.showwarning("Sin INF", "No hay INF Intel seleccionado.")
            return
        valid, msg, plan = self.action_service.validate_candidate(candidate, self.state, self._preferred_inf_path())
        self.log_human(msg)
        if not valid or not plan:
            messagebox.showwarning("Validación", msg)
            return

        confirm = (
            f"Se aplicará {plan.inf_path} sobre {plan.target_device}.\n"
            f"Origen: {'perfil preferido' if plan.using_preferred else 'selección/sistema'}\n"
            f"Motivo: {plan.source_reason}\n\n"
            "¿Desea continuar?"
        )
        if not messagebox.askyesno("Confirmar aplicación", confirm):
            return

        def worker() -> None:
            result = self.action_service.apply_and_verify(plan, self.state, block_updates=self.block_updates_var.get())
            self.log_human(f"Driver antes: {result.before_version} | después: {result.after_version}")
            if result.ok:
                self.log_human("Driver aplicado correctamente.")
                self.after(0, lambda: messagebox.showinfo("Resultado", result.message))
            else:
                if result.reverted:
                    self.log_error("Windows revirtió el driver automáticamente.")
                self.log_error(result.message)
                self.after(0, lambda: messagebox.showwarning("Fallo", result.message))
            self.refresh_all_async()

        self._run_bg("Aplicar controlador Intel objetivo", worker)

    def resolve_real_case(self) -> None:
        self.log_human("Modo 'Resolver mi caso real' ejecutado.")
        self.run_diagnostic()
        if self.intel_candidate:
            self.assistant_text.set(
                f"Resolver mi caso real: listo para aplicar {self.intel_candidate.source_path} sobre {self.state.intel_adapter}."
            )

    def run_diagnostic(self) -> None:
        def worker() -> None:
            state = self.system_service.get_system_state()
            comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, state)
            intel = self.inventory_service.autodetect_intel2115([Path(p) for p in self.user_config.normalized_paths()] + [Path.cwd(), Path.home()])
            result: DiagnosticResult = self.diagnostic_service.run(state, comparison, intel)
            self.after(0, lambda: self._show_diagnostic(result))

        self._run_bg("Diagnóstico para Meta Quest 3", worker)

    def _show_diagnostic(self, result: DiagnosticResult) -> None:
        self.log_human(result.summary)
        self.log_human(f"Siguiente paso sugerido: {result.next_step}")
        self.assistant_text.set(f"Resolver mi caso real: {result.summary} {result.next_step}")
        messagebox.showinfo("Diagnóstico", result.summary + "\n\n" + "\n".join(result.checklist) + "\n\n" + result.next_step)

    def reopen_as_admin(self) -> None:
        if os.name != "nt":
            messagebox.showwarning("Admin", "Solo disponible en Windows.")
            return
        try:
            import ctypes

            params = f'"{Path(__file__).resolve().parents[1] / "app.py"}"'
            rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            if rc <= 32:
                raise RuntimeError(f"ShellExecuteW retornó {rc}")
            self.log_human("Se solicitó reapertura como administrador.")
        except Exception as exc:
            messagebox.showerror("Admin", f"No se pudo reabrir como admin: {exc}")

    def export_technical_log(self) -> None:
        output = filedialog.asksaveasfilename(title="Guardar log técnico", defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if not output:
            return
        source = technical_log_path()
        if not source.exists():
            messagebox.showwarning("Log", "No hay log técnico disponible.")
            return
        Path(output).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        self.log_human(f"Log técnico exportado a: {output}")

    def reboot(self) -> None:
        if messagebox.askyesno("Reiniciar", "¿Reiniciar en 5 segundos?"):
            ok, detail = self.action_service.request_reboot()
            (self.log_human if ok else self.log_error)(detail)

    def load_profile(self) -> None:
        path = filedialog.askopenfilename(title="Cargar perfil", filetypes=[("Perfil txt", "*.txt")])
        if not path:
            return
        self.profile = self.profile_service.cargar_perfil(Path(path))
        self.profile_path = Path(path)
        self.log_human(f"Perfil cargado: {path}")
        self.refresh_all_async()

    def save_profile(self) -> None:
        self.profile.set("EQUIPO", "equipo", self.state.computer_name)
        self.profile.set("EQUIPO", "gpu", self.state.intel_adapter)
        self.profile.set("DRIVER", "version", self.state.intel_driver_version)
        self.profile.set("DRIVER", "inf", self.state.intel_inf_name)
        if self.intel_candidate:
            self.profile.set("RUTAS", "intel2115", self.intel_candidate.source_path)
        target = filedialog.asksaveasfilename(title="Guardar perfil", defaultextension=".txt", filetypes=[("Perfil txt", "*.txt")])
        if not target:
            return
        self.profile_service.guardar_perfil(Path(target), self.profile)
        self.log_human(f"Perfil guardado: {target}")

    def compare_profile(self) -> None:
        comp = self.profile_service.comparar_perfil_vs_sistema(self.profile, self.state)
        self.log_human(f"Comparación sistema vs perfil: {'coincide' if comp.matches else 'no coincide'}")
        messagebox.showinfo("Comparación", "\n".join(comp.details))


if __name__ == "__main__":
    app = DriverSwitchApp()
    app.mainloop()
