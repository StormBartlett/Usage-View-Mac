"""
Launches the dashboard window as a subprocess so its event loop
doesn't conflict with rumps.
"""
import subprocess
import sys
from pathlib import Path

_proc: subprocess.Popen | None = None
_SCRIPT = Path(__file__).parent / "dashboard_window.py"


def show_dashboard(tab_index: int = 0):
    global _proc
    # If already running, kill it and reopen at the new tab
    if _proc is not None and _proc.poll() is None:
        _proc.kill()
        _proc = None

    _proc = subprocess.Popen(
        [sys.executable, str(_SCRIPT), str(tab_index)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
