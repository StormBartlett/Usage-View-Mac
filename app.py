"""
Usage View — Mac menu bar app
Shows Claude Pro, Cursor Pro, and Codex (OpenAI) plan usage at a glance.
"""
import subprocess
import threading
from datetime import datetime

import rumps

from providers.claude import get_claude_status
from providers.codex import get_codex_usage
from providers.cursor import get_cursor_usage


class UsageApp(rumps.App):
    def __init__(self):
        super().__init__("📊", quit_button="Quit")

        self.claude_item = rumps.MenuItem("Claude Pro   loading…", callback=self.open_claude)
        self.cursor_item = rumps.MenuItem("Cursor Pro   loading…", callback=self.open_cursor)
        self.codex_item  = rumps.MenuItem("Codex        loading…", callback=self.open_codex)
        self.updated_item = rumps.MenuItem("Updated: —", callback=None)
        self.refresh_item = rumps.MenuItem("↻  Refresh", callback=self.refresh)

        self.menu = [
            self.claude_item,
            self.cursor_item,
            self.codex_item,
            None,
            self.updated_item,
            self.refresh_item,
        ]

        # Initial fetch
        self.refresh(None)

        # Auto-refresh every 5 minutes
        self._timer = rumps.Timer(self.refresh, 300)
        self._timer.start()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, _):
        thread = threading.Thread(target=self._fetch_all, daemon=True)
        thread.start()

    def _fetch_all(self):
        results = {}
        lock = threading.Lock()

        def run(name, fn):
            try:
                result = fn()
            except Exception as exc:
                result = {"connected": False, "error": str(exc)[:50]}
            with lock:
                results[name] = result

        threads = [
            threading.Thread(target=run, args=("claude", get_claude_status), daemon=True),
            threading.Thread(target=run, args=("cursor", get_cursor_usage), daemon=True),
            threading.Thread(target=run, args=("codex",  get_codex_usage),  daemon=True),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        self._update_menu(results)

    # ------------------------------------------------------------------
    # Menu update (called from background thread — rumps is thread-safe
    # for title assignments)
    # ------------------------------------------------------------------

    def _update_menu(self, results):
        self.claude_item.title = self._fmt_claude(results.get("claude", {}))
        self.cursor_item.title = self._fmt_cursor(results.get("cursor", {}))
        self.codex_item.title  = self._fmt_codex(results.get("codex",  {}))
        self.updated_item.title = f"Updated: {datetime.now().strftime('%H:%M:%S')}"

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_claude(d):
        label = "Claude Pro   "
        if not d.get("connected"):
            err = d.get("error", "not connected")
            return label + f"✗  {err}"
        plan = d.get("plan", "Pro")
        return label + f"✓  {plan} connected"

    @staticmethod
    def _fmt_cursor(d):
        label = "Cursor Pro   "
        if not d.get("connected"):
            err = d.get("error", "not connected")
            return label + f"✗  {err}"
        used  = d.get("requests_used")
        limit = d.get("requests_limit")
        if used is not None and limit:
            pct = used / limit * 100
            bar = _progress_bar(pct)
            return label + f"{bar}  {used}/{limit} ({pct:.0f}%)"
        if used is not None:
            return label + f"✓  {used} requests used"
        return label + "✓  connected"

    @staticmethod
    def _fmt_codex(d):
        label = "Codex        "
        if not d.get("connected"):
            err = d.get("error", "not connected")
            return label + f"✗  {err}"
        cost = d.get("total_cost")
        if cost is not None:
            return label + f"✓  ${cost:.2f} this month"
        tokens = d.get("total_tokens")
        if tokens is not None:
            return label + f"✓  {tokens:,} tokens this month"
        return label + "✓  connected"

    # ------------------------------------------------------------------
    # Open dashboards in browser
    # ------------------------------------------------------------------

    def open_claude(self, _):
        subprocess.run(["open", "https://claude.ai/settings"], check=False)

    def open_cursor(self, _):
        subprocess.run(["open", "https://www.cursor.com/settings"], check=False)

    def open_codex(self, _):
        subprocess.run(["open", "https://platform.openai.com/usage"], check=False)


# ------------------------------------------------------------------
# Tiny ASCII progress bar
# ------------------------------------------------------------------

def _progress_bar(pct: float, width: int = 8) -> str:
    filled = round(pct / 100 * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


# ------------------------------------------------------------------

if __name__ == "__main__":
    UsageApp().run()
