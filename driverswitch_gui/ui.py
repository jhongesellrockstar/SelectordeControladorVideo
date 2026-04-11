from __future__ import annotations

import os
import queue
import subprocess
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
from driverswitch_gui.services.driver_actions import DriverActionService
from driverswitch_gui.services.driver_inventory import DriverInventoryService
from driverswitch_gui.services.profile_service import ProfileService
from driverswitch_gui.services.system_info import SystemInfoService, SystemState

MIXED_REALITY_TARGET = "31.0.101.2115"


class DriverSwitchApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DriverSwitch GUI - Selector de controlador de video")
        self.geometry("1400x820")

        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.logger = build_logger()
        self.config_store = ConfigStore()
        self.user_config = self.config_store.load()

        self.state = SystemState("-", "-", "-", "-", "-", "-", "")
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
        self.after(150, self.startup_load)

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=6)
        self.lbl_system = ttk.Label(top, text="Equipo detectado: cargando...")
        self.lbl_system.grid(row=0, column=0, sticky="w", padx=4)
        self.lbl_adapter = ttk.Label(top, text="GPU activa: cargando...")
        self.lbl_adapter.grid(row=0, column=1, sticky="w", padx=4)
        self.lbl_version = ttk.Label(top, text="Driver activo: cargando...")
        self.lbl_version.grid(row=0, column=2, sticky="w", padx=4)
        self.lbl_inf = ttk.Label(top, text="INF activo: cargando...")
        self.lbl_inf.grid(row=1, column=0, sticky="w", padx=4)
        self.lbl_provider = ttk.Label(top, text="Proveedor: cargando...")
        self.lbl_provider.grid(row=1, column=1, sticky="w", padx=4)
        self.lbl_profile_state = ttk.Label(top, text="Estado vs perfil: pendiente")
        self.lbl_profile_state.grid(row=1, column=2, sticky="w", padx=4)

        self.lbl_mr = ttk.Label(top, text="Compatibilidad RM: pendiente", foreground="#884400")
        self.lbl_mr.grid(row=2, column=0, columnspan=3, sticky="w", padx=4)

        self.assistant_text = tk.StringVar(value="¿Qué hizo el software?: iniciando...")
        ttk.Label(self, textvariable=self.assistant_text, background="#f3f7ff", anchor="w").pack(fill="x", padx=10, pady=(2, 8))

        center = ttk.Panedwindow(self, orient="vertical")
        center.pack(fill="both", expand=True, padx=10, pady=4)

        table_frame = ttk.Frame(center)
        center.add(table_frame, weight=3)
        columns = ("origen", "proveedor", "version", "fecha", "inf", "estado", "preferido")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        for key, title in {
            "origen": "Origen",
            "proveedor": "Proveedor",
            "version": "Versión",
            "fecha": "Fecha",
            "inf": "INF",
            "estado": "Estado",
            "preferido": "Preferido",
        }.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=175 if key != "estado" else 240, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        bottom_tabs = ttk.Notebook(center)
        center.add(bottom_tabs, weight=2)

        log_frame = ttk.Frame(bottom_tabs)
        bottom_tabs.add(log_frame, text="Log en tiempo real")
        self.log_widget = tk.Text(log_frame, height=10, wrap="word", state="disabled", bg="#10161f", fg="#d3f0ff")
        self.log_widget.pack(fill="both", expand=True)

        help_frame = ttk.Frame(bottom_tabs)
        bottom_tabs.add(help_frame, text="Primeros pasos")
        help_text = tk.Text(help_frame, height=10, wrap="word")
        help_text.insert(
            "1.0",
            "Flujo recomendado para resolver tu caso real (Meta Quest 3):\n"
            "1) Pulsa 'Diagnosticar mi equipo'.\n"
            "2) Si indica incompatibilidad, usa 'Agregar carpeta INF' o valida Intel2115 detectado.\n"
            "3) Selecciona la fila Intel2115 (iigd_dch.inf).\n"
            "4) Pulsa 'Aplicar controlador'.\n"
            "5) Reinicia el equipo y vuelve a ejecutar 'Diagnosticar mi equipo'.\n"
            "6) Si muestra versión 31.0.101.2115, prueba Windows App / vínculo RM.\n\n"
            "Qué hace cada botón: leer estado, buscar drivers, aplicar cambios, comparar perfil y exportar logs."
        )
        help_text.configure(state="disabled")
        help_text.pack(fill="both", expand=True)

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=5)
        buttons = [
            ("Diagnosticar mi equipo", self.run_diagnostic),
            ("Refrescar estado", self.refresh_all_async),
            ("Agregar carpeta INF", self.add_external_folder),
            ("Marcar como preferido", self.mark_preferred),
            ("Aplicar controlador", self.apply_selected),
            ("Refrescar adaptador", self.refresh_adapter),
            ("Abrir carpeta", self.open_folder),
            ("Modo recuperación", self.quick_recovery),
            ("Exportar log técnico", self.export_technical_log),
            ("Reiniciar equipo", self.reboot),
            ("Cargar perfil", self.load_profile),
            ("Guardar perfil", self.save_profile),
            ("Nuevo perfil", self.new_profile),
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
            line = f"[{ts}] {msg}\n"
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", line)
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")
            if level == "ERROR":
                self.status_var.set(msg)
        self.after(150, self._drain_log_queue)

    def startup_load(self) -> None:
        self.log_human("Inicio de aplicación. Cargando perfil y diagnóstico inicial en segundo plano...")
        self.profile = self._load_default_profile()
        self.refresh_all_async()

    def _run_bg(self, label: str, target) -> None:
        def runner() -> None:
            self.log_human(f"Tarea iniciada: {label}")
            t0 = time.perf_counter()
            try:
                target()
            except Exception as exc:  # robustez de GUI
                self.log_error(f"Error en tarea '{label}': {exc}")
            elapsed = time.perf_counter() - t0
            self.log_human(f"Tarea finalizada: {label} ({elapsed:.2f}s)")

        threading.Thread(target=runner, daemon=True).start()

    def _load_default_profile(self) -> ProfileData:
        if self.profile_path.exists():
            self.log_human(f"Cargando perfil por defecto: {self.profile_path}")
            try:
                return self.profile_service.cargar_perfil(self.profile_path)
            except OSError as exc:
                self.log_error(f"No se pudo cargar perfil por defecto: {exc}")
        self.log_human("No existe perfil base. Se creará perfil vacío.")
        profile = self.profile_service.crear_perfil_vacio()
        self.profile_service.guardar_perfil(self.profile_path, profile)
        return profile

    def refresh_all_async(self) -> None:
        self._run_bg("Actualizar estado general", self._refresh_all_worker)

    def _refresh_all_worker(self) -> None:
        state = self.system_service.get_system_state()
        candidates = self.inventory_service.list_driver_store(active_inf=state.inf_name)
        for path in self.user_config.normalized_paths():
            candidates.extend(self.inventory_service.scan_external_folder(Path(path)))

        intel = self.inventory_service.autodetect_intel2115([Path.cwd(), Path.home()])
        if intel and all(c.source_path != intel.source_path for c in candidates):
            candidates.append(intel)
            if not self.user_config.preferred_inf:
                self.user_config.preferred_inf = intel.inf_name
                self.user_config.preferred_version = intel.version
                self.config_store.save(self.user_config)
                self.log_human("Intel2115 marcado automáticamente como preferido.")

        comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, state)
        self.log_human(f"Comparación sistema vs perfil: {'coincide' if comparison.matches else 'no coincide'}")

        self.after(0, lambda: self._apply_refresh_results(state, candidates, intel, comparison))

    def _apply_refresh_results(
        self,
        state: SystemState,
        candidates: list[DriverCandidate],
        intel: DriverCandidate | None,
        comparison: ProfileComparison,
    ) -> None:
        self.state = state
        self.candidates = candidates
        self.intel_candidate = intel
        self.profile_comparison = comparison

        self.lbl_system.config(text=f"Equipo detectado: {state.computer_name}")
        self.lbl_adapter.config(text=f"GPU activa: {state.active_adapter}")
        self.lbl_version.config(text=f"Driver activo: {state.driver_version} ({state.driver_date})")
        self.lbl_inf.config(text=f"INF activo: {state.inf_name}")
        self.lbl_provider.config(text=f"Proveedor activo: {state.provider}")
        self.lbl_profile_state.config(text=f"Estado vs perfil: {'coincide' if comparison.matches else 'difiere'}")

        if state.driver_version != MIXED_REALITY_TARGET:
            self.lbl_mr.config(text=f"Advertencia: Meta Quest 3 recomienda {MIXED_REALITY_TARGET}.", foreground="#a14b00")
            self.log_human(f"Advertencia: Meta Quest 3 recomienda {MIXED_REALITY_TARGET}")
        else:
            self.lbl_mr.config(text="Compatibilidad RM correcta: versión objetivo detectada.", foreground="#116611")
            self.log_human("Compatibilidad RM: versión objetivo activa.")

        self._render_table()
        self._update_assistant_message()
        self.status_var.set("Estado actualizado")

    def _render_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)

        preferred_match = (self.user_config.preferred_inf, self.user_config.preferred_version)
        for idx, c in enumerate(self.candidates):
            preferred = "Sí" if (c.inf_name, c.version) == preferred_match else "No"
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(c.source_type, c.provider, c.version, c.driver_date, c.inf_name, c.status, preferred),
            )

    def _update_assistant_message(self) -> None:
        if self.state.driver_version == MIXED_REALITY_TARGET:
            text = (
                "¿Qué hizo el software?: detectó que ya usas la versión recomendada para Meta Quest 3. "
                "Siguiente paso: probar conexión en Windows App / Vínculo RM."
            )
        elif self.intel_candidate:
            text = (
                "¿Qué hizo el software?: detectó que tu driver actual no coincide con Meta Quest 3, "
                "pero encontró Intel2115 (iigd_dch.inf). Siguiente paso: seleccionarlo y pulsar 'Aplicar controlador'."
            )
        else:
            text = (
                "¿Qué hizo el software?: detectó incompatibilidad y no encontró Intel2115 automáticamente. "
                "Siguiente paso: usar 'Agregar carpeta INF' y luego 'Aplicar controlador'."
            )
        self.assistant_text.set(text)

    def _selected_candidate(self) -> DriverCandidate | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return self.candidates[int(selected[0])]

    def add_external_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona carpeta con INF exportados")
        if not folder:
            return
        self.log_human(f"Botón: Agregar carpeta INF ({folder})")
        detected = self.inventory_service.scan_external_folder(Path(folder))
        if not detected:
            messagebox.showwarning("Carpeta inválida", "No se encontraron controladores de pantalla compatibles.")
            return
        paths = set(self.user_config.normalized_paths())
        paths.add(folder)
        self.user_config.external_paths = sorted(paths)
        self.config_store.save(self.user_config)
        self.refresh_all_async()

    def mark_preferred(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            messagebox.showinfo("Sin selección", "Selecciona una versión en la tabla.")
            return
        self.user_config.preferred_inf = candidate.inf_name
        self.user_config.preferred_version = candidate.version
        self.config_store.save(self.user_config)
        self.log_human(f"Preferido actualizado: {candidate.inf_name} {candidate.version}")
        self.refresh_all_async()

    def apply_selected(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            messagebox.showinfo("Sin selección", "Selecciona una versión en la tabla.")
            return
        valid, msg = self.action_service.validate_candidate(candidate, self.state)
        self.log_human(f"Validación de compatibilidad: {msg}")
        if not valid:
            messagebox.showwarning("Compatibilidad", msg)
            return
        if not messagebox.askyesno("Confirmar cambio", f"{msg}\n\n¿Aplicar controlador ahora?"):
            return

        def worker() -> None:
            ok, detail = self.action_service.apply_and_refresh(candidate, self.state.pnp_device_id)
            if ok:
                self.log_human("Controlador aplicado correctamente.")
                self.after(0, lambda: messagebox.showinfo("Resultado", detail))
                self.refresh_all_async()
            else:
                self.log_error(f"No se pudo aplicar el controlador: {detail}")
                self.after(0, lambda: messagebox.showwarning("Error", detail))

        self._run_bg("Aplicar controlador", worker)

    def refresh_adapter(self) -> None:
        self.log_human("Botón: Refrescar adaptador")

        def worker() -> None:
            ok, detail = self.action_service.refresh_adapter(self.state.pnp_device_id)
            if ok:
                self.log_human(detail)
            else:
                self.log_error(detail)
            self.after(0, lambda: messagebox.showinfo("Refrescar adaptador", detail))

        self._run_bg("Refrescar adaptador", worker)

    def open_folder(self) -> None:
        candidate = self._selected_candidate()
        if not candidate:
            return
        folder = candidate.folder_hint
        if not folder:
            messagebox.showinfo("Sin carpeta", "Este elemento no tiene ruta local asociada.")
            return
        self.log_human(f"Abriendo carpeta: {folder}")
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)

    def quick_recovery(self) -> None:
        self.log_human("Botón: Modo recuperación")
        if not self.user_config.preferred_inf:
            messagebox.showinfo("Recuperación", "No existe controlador preferido guardado.")
            return
        candidate = next((c for c in self.candidates if c.inf_name == self.user_config.preferred_inf and c.version == self.user_config.preferred_version), None)
        if not candidate:
            messagebox.showwarning("Recuperación", "El controlador preferido no está disponible en inventario.")
            return
        self.tree.selection_set(str(self.candidates.index(candidate)))
        self.apply_selected()

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
        if not messagebox.askyesno("Reiniciar", "¿Deseas reiniciar el equipo en 5 segundos?"):
            return
        ok, detail = self.action_service.request_reboot()
        if ok:
            self.log_human(detail)
        else:
            self.log_error(detail)

    def load_profile(self) -> None:
        path = filedialog.askopenfilename(title="Cargar perfil", filetypes=[("Perfil txt", "*.txt")])
        if not path:
            return
        self.profile = self.profile_service.cargar_perfil(Path(path))
        self.profile_path = Path(path)
        self.log_human(f"Perfil cargado: {path}")
        self.compare_profile()

    def save_profile(self) -> None:
        if not self.profile.sections:
            self.profile = self.profile_service.crear_perfil_vacio()
        self.profile.set("EQUIPO", "equipo", self.state.computer_name)
        self.profile.set("EQUIPO", "gpu", self.state.active_adapter)
        self.profile.set("DRIVER", "provider", self.state.provider)
        self.profile.set("DRIVER", "version", self.state.driver_version)
        self.profile.set("DRIVER", "inf", self.state.inf_name)
        target = filedialog.asksaveasfilename(title="Guardar perfil", defaultextension=".txt", filetypes=[("Perfil txt", "*.txt")])
        if not target:
            return
        self.profile_service.guardar_perfil(Path(target), self.profile)
        self.profile_path = Path(target)
        self.log_human(f"Perfil guardado: {target}")

    def new_profile(self) -> None:
        self.profile = self.profile_service.crear_perfil_vacio()
        self.log_human("Se creó perfil vacío.")
        messagebox.showinfo("Perfil", "Se creó un perfil vacío.")

    def compare_profile(self) -> None:
        self.profile_comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, self.state)
        self.lbl_profile_state.config(text=f"Estado vs perfil: {'coincide' if self.profile_comparison.matches else 'difiere'}")
        self.log_human(f"Comparación sistema vs perfil: {'coincide' if self.profile_comparison.matches else 'no coincide'}")
        messagebox.showinfo("Comparación", "\n".join(self.profile_comparison.details))

    def run_diagnostic(self) -> None:
        self.log_human("Botón: Diagnosticar mi equipo")

        def worker() -> None:
            state = self.system_service.get_system_state()
            comparison = self.profile_service.comparar_perfil_vs_sistema(self.profile, state)
            intel = self.inventory_service.autodetect_intel2115([Path.cwd(), Path.home()])
            result: DiagnosticResult = self.diagnostic_service.run(state, comparison, intel)
            self.after(0, lambda: self._show_diagnostic_result(result))

        self._run_bg("Diagnóstico para Meta Quest 3", worker)

    def _show_diagnostic_result(self, result: DiagnosticResult) -> None:
        title = "Diagnóstico: problema resuelto" if result.ok else "Diagnóstico: acción requerida"
        detail = result.summary + "\n\n" + "\n".join(f"- {line}" for line in result.checklist) + "\n\nSiguiente paso:\n" + result.next_step
        self.assistant_text.set(f"¿Qué hizo el software?: {result.summary} Siguiente paso: {result.next_step}")
        self.log_human(result.summary)
        self.log_human(f"Siguiente paso sugerido: {result.next_step}")
        messagebox.showinfo(title, detail)


if __name__ == "__main__":
    app = DriverSwitchApp()
    app.mainloop()
