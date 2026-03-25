#!/usr/bin/env python3
"""
Standalone dashboard window launched as a subprocess.
Runs its own event loop so it doesn't conflict with rumps.

Usage: python3 dashboard_window.py [tab_index]
"""
import sys

import webview

TABS = [
    ("Claude",  "https://claude.ai/settings/usage"),
    ("Cursor",  "https://cursor.com/dashboard/spending"),
    ("Codex",   "https://chatgpt.com/codex/settings/usage"),
]

HTML_CHROME = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a1a; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; height: 100vh; }
  #tab-bar { display: flex; background: #111; padding: 6px 8px 0; gap: 4px; flex-shrink: 0; }
  .tab {
    padding: 7px 20px; border-radius: 8px 8px 0 0; cursor: pointer;
    font-size: 13px; font-weight: 600; color: #888; border: none; background: #1e1e1e;
    transition: color .15s, background .15s;
  }
  .tab.active { background: #2a2a2a; color: #fff; }
  .tab:hover:not(.active) { color: #bbb; }
  .tab[data-i="0"].active { color: #d47848; }
  .tab[data-i="1"].active { color: #2e87e8; }
  .tab[data-i="2"].active { color: #35ae7c; }
  #frame-wrap { flex: 1; background: #000; }
  iframe { width: 100%; height: 100%; border: none; display: block; }
</style>
</head>
<body>
<div id="tab-bar">
  <button class="tab" data-i="0" onclick="switchTab(0)">Claude</button>
  <button class="tab" data-i="1" onclick="switchTab(1)">Cursor</button>
  <button class="tab" data-i="2" onclick="switchTab(2)">Codex</button>
</div>
<div id="frame-wrap">
  <iframe id="frame" src=""></iframe>
</div>
<script>
  const URLS = {urls_json};
  let current = {initial_tab};

  function switchTab(i) {{
    document.querySelectorAll('.tab').forEach((t, idx) => t.classList.toggle('active', idx === i));
    document.getElementById('frame').src = URLS[i];
    current = i;
  }}

  switchTab(current);
</script>
</body>
</html>
"""


def main():
    initial = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    urls_json = str([url for _, url in TABS])
    html = (
        HTML_CHROME
        .replace("{urls_json}", urls_json)
        .replace("{initial_tab}", str(initial))
    )

    window = webview.create_window(
        "Usage Dashboards",
        html=html,
        width=1_150,
        height=800,
        min_size=(700, 500),
    )
    webview.start()


if __name__ == "__main__":
    main()
