from __future__ import annotations

import tkinter as tk


class LogPanel(tk.Text):
    def append(self, text: str) -> None:
        self.configure(state="normal")
        self.insert("end", text + "\n")
        self.see("end")
        self.configure(state="disabled")
