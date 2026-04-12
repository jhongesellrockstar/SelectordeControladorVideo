from __future__ import annotations

import os
import subprocess
from typing import Any


def _hidden_process_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


def run_hidden(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
    kw = _hidden_process_kwargs()
    kw.update(kwargs)
    return subprocess.run(*args, **kw)


def popen_hidden(*args: Any, **kwargs: Any) -> subprocess.Popen:
    kw = _hidden_process_kwargs()
    kw.update(kwargs)
    return subprocess.Popen(*args, **kw)
