"""
Claude provider — detects Anthropic API key and validates it.

Claude Pro doesn't expose a usage API, so we just confirm connectivity
and let the user click through to claude.ai/settings for the full picture.
"""
import json
import os
from pathlib import Path

import requests

TIMEOUT = 6


def get_claude_status() -> dict:
    api_key = _find_api_key()
    if not api_key:
        return {"connected": False, "error": "no API key found"}

    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return {"connected": False, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"connected": False, "error": "no internet"}
    except Exception as exc:
        return {"connected": False, "error": str(exc)[:40]}

    if resp.status_code == 200:
        return {"connected": True, "plan": "Pro"}
    if resp.status_code == 401:
        return {"connected": False, "error": "invalid API key"}
    return {"connected": False, "error": f"HTTP {resp.status_code}"}


# ---------------------------------------------------------------------------
# Key discovery — checks common locations in order of preference
# ---------------------------------------------------------------------------

def _find_api_key() -> str | None:
    # 1. Environment variable (most common)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 2. Claude Code stores the key in ~/.claude.json
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        try:
            data = json.loads(claude_json.read_text())
            key = data.get("primaryApiKey") or data.get("apiKey") or data.get("api_key")
            if key:
                return key
        except Exception:
            pass

    # 3. Plain text file (some users put it here)
    for path in [
        Path.home() / ".anthropic" / "api_key",
        Path.home() / ".config" / "anthropic" / "api_key",
    ]:
        if path.exists():
            key = path.read_text().strip()
            if key:
                return key

    return None
