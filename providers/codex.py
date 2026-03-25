"""
Codex / OpenAI provider — auto-discovers API key from Codex CLI config or
$OPENAI_API_KEY and fetches billing usage.  Falls back to "subscribed".
"""
import json
import os
from datetime import date
from pathlib import Path

import requests

TIMEOUT = 8


def get_codex_usage() -> dict:
    api_key = _find_api_key()
    if not api_key:
        return {"connected": True, "note": "add OPENAI_API_KEY for usage stats"}

    headers = {"Authorization": f"Bearer {api_key}"}
    today = date.today()
    start = today.replace(day=1).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    # Primary: dashboard billing endpoint
    try:
        resp = requests.get(
            f"https://api.openai.com/dashboard/billing/usage"
            f"?start_date={start}&end_date={end}",
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            cost = data.get("total_usage", 0) / 100.0
            return {"connected": True, "total_cost": cost}
        if resp.status_code == 401:
            return {"connected": True, "note": "API key invalid"}
    except requests.exceptions.Timeout:
        return {"connected": True, "note": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"connected": True, "note": "offline"}
    except Exception:
        pass

    # Fallback: v1 usage (token counts)
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

    return {"connected": True}


def _find_api_key() -> str | None:
    # 1. Environment variables
    for var in ("OPENAI_API_KEY", "CODEX_API_KEY"):
        key = os.environ.get(var, "").strip()
        if key:
            return key

    # 2. Codex CLI auth: ~/.codex/auth.json
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
            import tomllib
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            key = data.get("token") or data.get("api_key")
            if key:
                return key
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

    # 4. Legacy plain-text
    legacy = Path.home() / ".openai" / "api_key"
    if legacy.exists():
        key = legacy.read_text().strip()
        if key:
            return key

    return None
