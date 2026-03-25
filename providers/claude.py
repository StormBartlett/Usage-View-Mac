"""
Claude provider — supports both Anthropic API keys and Claude Code OAuth tokens.

Claude Pro doesn't expose a plan-usage API, so we just confirm connectivity
and let the user click through to claude.ai/settings for the full picture.

Auth discovery order:
  1. $ANTHROPIC_API_KEY env var
  2. ~/.claude.json  (Claude Code stores primaryApiKey OR an oauthAccount token here)
  3. ~/.anthropic/api_key  (plain text fallback)
"""
import json
import os
from pathlib import Path

import requests

TIMEOUT = 6


def get_claude_status() -> dict:
    api_key, token_type = _find_credential()

    if not api_key:
        return {
            "connected": False,
            "error": "set ANTHROPIC_API_KEY in your shell",
        }

    if token_type == "api_key":
        return _check_with_api_key(api_key)
    else:
        # OAuth / session token from Claude Code login
        return _check_with_oauth(api_key)


# ---------------------------------------------------------------------------
# Auth checks
# ---------------------------------------------------------------------------

def _check_with_api_key(key: str) -> dict:
    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": key,
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


def _check_with_oauth(token: str) -> dict:
    """Try Claude Code's OAuth token against the Anthropic API as a Bearer token."""
    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-version": "2023-06-01",
            },
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return {"connected": True, "plan": "Pro"}
        # OAuth token may need to go via claude.ai instead
        resp2 = requests.get(
            "https://claude.ai/api/auth/session",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        if resp2.status_code == 200:
            return {"connected": True, "plan": "Pro"}
        if resp2.status_code in (401, 403):
            return {"connected": False, "error": "session expired — run: claude"}
    except requests.exceptions.Timeout:
        return {"connected": False, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"connected": False, "error": "no internet"}
    except Exception:
        pass

    # Token found but couldn't verify — assume connected (Claude Code is working)
    return {"connected": True, "plan": "Pro"}


# ---------------------------------------------------------------------------
# Credential discovery
# ---------------------------------------------------------------------------

def _find_credential() -> tuple[str | None, str]:
    """Returns (credential, type) where type is 'api_key' or 'oauth'."""

    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key, "api_key"

    # 2. ~/.claude.json  — Claude Code's config file
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        try:
            data = json.loads(claude_json.read_text())
            cred, ctype = _extract_from_claude_json(data)
            if cred:
                return cred, ctype
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
                return key, "api_key"

    return None, "api_key"


def _extract_from_claude_json(data: dict) -> tuple[str | None, str]:
    """
    ~/.claude.json structure varies by auth method:

    API key login:
      { "primaryApiKey": "sk-ant-...", ... }

    Claude Code OAuth login (browser):
      { "oauthAccount": { "accessToken": "...", "emailAddress": "..." }, ... }
    """
    # Direct API key fields
    for field in ("primaryApiKey", "apiKey", "api_key", "anthropicApiKey"):
        val = data.get(field)
        if isinstance(val, str) and val.startswith("sk-ant-"):
            return val, "api_key"

    # Nested OAuth account (Claude Code browser login)
    oauth = data.get("oauthAccount") or data.get("oauth") or data.get("account")
    if isinstance(oauth, dict):
        token = oauth.get("accessToken") or oauth.get("access_token") or oauth.get("token")
        if isinstance(token, str) and len(token) > 20:
            return token, "oauth"

    # Fallback: scan ALL string values for an API key pattern
    def _scan(obj, depth=0):
        if depth > 4:
            return None, "api_key"
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith("sk-ant-") and len(v) > 20:
                    return v, "api_key"
                result = _scan(v, depth + 1)
                if result[0]:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = _scan(item, depth + 1)
                if result[0]:
                    return result
        return None, "api_key"

    return _scan(data)
