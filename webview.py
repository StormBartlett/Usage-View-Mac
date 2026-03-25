"""Opens the relevant usage dashboard in the default browser."""
import webbrowser

_URLS = [
    "https://claude.ai/settings/usage",
    "https://cursor.com/dashboard/spending",
    "https://chatgpt.com/codex/settings/usage",
]


def show_dashboard(tab_index: int = 0):
    webbrowser.open(_URLS[tab_index])
