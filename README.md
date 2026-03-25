# Usage View — Mac Menu Bar

A lightweight menu bar app showing your **Claude Pro**, **Cursor Pro**, and **Codex (OpenAI)** usage at a glance.

```
📊
├── Claude Pro   ✓  Pro connected          → claude.ai/settings
├── Cursor Pro   [████░░░░]  320/500 (64%) → cursor.com/settings
├── Codex        ✓  $2.41 this month       → platform.openai.com/usage
├── ─────────────────────────────
├── Updated: 14:32:07
├── ↻  Refresh
└── Quit
```

Clicking any service row opens its dashboard in your browser.
The app auto-refreshes every **5 minutes**.

---

## Requirements

- macOS 12+
- Python 3.11+

## Setup

```bash
cd Usage-View-Mac
bash setup.sh          # install dependencies
python3 app.py         # run
```

### Start at login

```bash
python3 launch_agent.py install    # add Launch Agent
python3 launch_agent.py uninstall  # remove it
```

---

## API key detection

The app auto-detects credentials — no config file needed in most cases.

| Service | Where it looks |
|---------|---------------|
| **Claude** | `$ANTHROPIC_API_KEY` → `~/.claude.json` → `~/.anthropic/api_key` |
| **Codex** | `$OPENAI_API_KEY` / `$CODEX_API_KEY` → `~/.codex/auth.json` → `~/.codex/config.toml` |
| **Cursor** | Cursor's local SQLite store at `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` (sign in to Cursor at least once) |

> **Claude Pro note:** Anthropic doesn't expose a plan-usage API for Pro subscribers.
> The app confirms your API key is valid and links to `claude.ai/settings` for the real usage meter.

---

## Adding providers

Drop a new file in `providers/` that exports a function returning a dict:

```python
def get_myservice_status() -> dict:
    # must return {"connected": bool, ...extra keys...}
    ...
```

Then wire it up in `app.py`.
