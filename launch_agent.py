"""
Installs / removes a macOS Launch Agent so Usage View starts at login.

Usage:
    python3 launch_agent.py install
    python3 launch_agent.py uninstall
"""
import os
import subprocess
import sys
from pathlib import Path

LABEL = "com.usageview.app"
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = PLIST_DIR / f"{LABEL}.plist"


def install():
    python = sys.executable
    app = Path(__file__).parent.resolve() / "app.py"
    log_dir = Path.home() / "Library" / "Logs" / "UsageView"
    log_dir.mkdir(parents=True, exist_ok=True)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{app}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{log_dir}/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/stderr.log</string>
</dict>
</plist>
"""

    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist)

    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=False)
    print(f"Installed launch agent → {PLIST_PATH}")
    print("Usage View will now start automatically at login.")


def uninstall():
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=False)
        PLIST_PATH.unlink()
        print("Launch agent removed.")
    else:
        print("No launch agent found.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    else:
        print(__doc__)
        sys.exit(1)
