"""
Claude provider — auto-discovers Anthropic API key or Claude Code OAuth token
and validates connectivity.  Falls back to "subscribed" when no creds found.

Claude Pro doesn't expose a consumer usage API, so at best we confirm
connectivity and the user clicks through to claude.ai/settings for details.
"""
import json
import os
from pathlib import Path

import requests

TIMEOUT = 6


def get_claude_status() -> dict:
    api_key = _find_api_key()
    if not api_key:
        # No creds found — still show as subscribed, with hint
        return {"connected": True, "plan": "Pro", "note": "add API key for details"}

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
        return {"connected": True, "plan": "Pro", "note": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"connected": True, "plan": "Pro", "note": "offline"}
    except Exception:
        return {"connected": True, "plan": "Pro"}

    if resp.status_code == 200:
        return {"connected": True, "plan": "Pro", "verified": True}
    if resp.status_code == 401:
        return {"connected": True, "plan": "Pro", "note": "key invalid"}
    return {"connected": True, "plan": "Pro"}


def _find_api_key() -> str | None:
    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 2. Claude Code config: ~/.claude.json
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        try:
            data = json.loads(claude_json.read_text())
            # Direct API key fields
            for field in ("primaryApiKey", "apiKey", "api_key"):
                val = data.get(field)
                if isinstance(val, str) and val.strip().startswith("sk-ant-"):
                    return val.strip()
            # OAuth account (Claude Code browser login)
            oauth = data.get("oauthAccount") or data.get("oauth")
            if isinstance(oauth, dict):
                tok = oauth.get("accessToken") or oauth.get("access_token")
                if isinstance(tok, str) and len(tok) > 20:
                    return tok
        except Exception:
            pass

    # 3. Plain text fallback
    for path in [
        Path.home() / ".anthropic" / "api_key",
        Path.home() / ".config" / "anthropic" / "api_key",
    ]:
        if path.exists():
            key = path.read_text().strip()
            if key:
                return key

    return None
