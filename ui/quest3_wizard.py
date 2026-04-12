from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Quest3Wizard(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_diagnose, on_safe_repair, on_advanced_repair, on_generate_report) -> None:
        super().__init__(master)
        self.title("Modo reparación Quest 3")
        self.geometry("780x480")
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text="Asistente Quest 3 (Acer A315-57G)", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=8)
        self.timeline = tk.Text(self, height=14, wrap="word")
        self.timeline.pack(fill="both", expand=True, padx=10, pady=6)
        self.timeline.insert("end", "1) Diagnosticar estado actual.\n2) Reparación segura.\n3) Reparación avanzada (si aplica).\n4) Generar reporte y validar tras reinicio.\n")
        self.timeline.configure(state="disabled")

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=8)
        ttk.Button(actions, text="Paso 1: Diagnosticar", command=on_diagnose).pack(side="left", padx=4)
        ttk.Button(actions, text="Paso 2A: Reparación segura", command=on_safe_repair).pack(side="left", padx=4)
        ttk.Button(actions, text="Paso 2B: Reparación avanzada", command=on_advanced_repair).pack(side="left", padx=4)
        ttk.Button(actions, text="Paso 3: Generar reporte", command=on_generate_report).pack(side="left", padx=4)
