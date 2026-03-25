"""
Codex / OpenAI provider — reads the API key from ~/.codex/auth.json or
$OPENAI_API_KEY and fetches current-month billing usage from OpenAI's API.
"""
import json
import os
import tomllib
from datetime import date
from pathlib import Path

import requests

TIMEOUT = 8


def get_codex_usage() -> dict:
    api_key = _find_api_key()
    if not api_key:
        return {"connected": False, "error": "no API key found"}

    headers = {"Authorization": f"Bearer {api_key}"}
    today = date.today()
    start = today.replace(day=1).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")

    # Primary: dashboard billing endpoint (works for personal API keys)
    try:
        resp = requests.get(
            f"https://api.openai.com/dashboard/billing/usage"
            f"?start_date={start}&end_date={end}",
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            # total_usage is in cents
            cost = data.get("total_usage", 0) / 100.0
            return {"connected": True, "total_cost": cost}
        if resp.status_code == 401:
            return {"connected": False, "error": "invalid API key"}
    except requests.exceptions.Timeout:
        return {"connected": False, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"connected": False, "error": "no internet"}
    except Exception as exc:
        return {"connected": False, "error": str(exc)[:40]}

    # Fallback: v1 usage endpoint (token counts, not dollar amount)
    return _try_v1_usage(headers, today)


def _try_v1_usage(headers: dict, today: date) -> dict:
    try:
        resp = requests.get(
            f"https://api.openai.com/v1/usage?date={today.strftime('%Y-%m-%d')}",
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            total = sum(
                item.get("n_context_tokens_total", 0)
                + item.get("n_generated_tokens_total", 0)
                for item in data.get("data", [])
            )
            return {"connected": True, "total_tokens": total}
    except Exception:
        pass

    return {"connected": True}  # key valid but no usage data available


# ---------------------------------------------------------------------------
# Key discovery
# ---------------------------------------------------------------------------

def _find_api_key() -> str | None:
    # 1. Environment variables
    for var in ("OPENAI_API_KEY", "CODEX_API_KEY"):
        key = os.environ.get(var, "").strip()
        if key:
            return key

    # 2. Codex CLI auth file: ~/.codex/auth.json
    auth_path = Path.home() / ".codex" / "auth.json"
    if auth_path.exists():
        try:
            data = json.loads(auth_path.read_text())
            key = (
                data.get("api_key")
                or data.get("apiKey")
                or data.get("token")
                or data.get("openai_api_key")
            )
            if key:
                return key
        except Exception:
            pass

    # 3. Codex CLI config: ~/.codex/config.toml
    config_path = Path.home() / ".codex" / "config.toml"
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            # top-level token field
            key = data.get("token") or data.get("api_key")
            if key:
                return key
            # inside [model_providers.*]
            for provider in data.get("model_providers", {}).values():
                env_key_name = provider.get("env_key")
                if env_key_name:
                    val = os.environ.get(env_key_name, "").strip()
                    if val:
                        return val
                tok = provider.get("token")
                if tok:
                    return tok
        except Exception:
            pass

    # 4. Legacy plain-text file (some tools write it here)
    legacy = Path.home() / ".openai" / "api_key"
    if legacy.exists():
        key = legacy.read_text().strip()
        if key:
            return key

    return None
