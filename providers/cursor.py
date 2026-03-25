"""
Cursor provider — reads the auth token from Cursor's local SQLite store
then queries the Cursor usage API for real request/credit counts.

Falls back to "subscribed" when no token is found.

Token location (macOS):
  ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
  Table: ItemTable, key = 'cursorAuth/accessToken'
"""
import json
import sqlite3
from pathlib import Path

import requests

TIMEOUT = 8

USAGE_ENDPOINTS = [
    "https://www.cursor.com/api/usage",
    "https://api2.cursor.sh/auth/usage",
    "https://api2.cursor.sh/usage",
]


def get_cursor_usage() -> dict:
    token, email = _find_cursor_auth()

    if not token:
        return {"connected": True, "note": "open Cursor IDE to enable usage stats"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    for url in USAGE_ENDPOINTS:
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                parsed = _parse_usage(data)
                return {"connected": True, **parsed}
            if resp.status_code == 401:
                return {
                    "connected": True,
                    "note": "token expired — reopen Cursor IDE app to refresh",
                }
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            return {"connected": True, "note": "offline"}
        except Exception:
            continue

    # Token found but no endpoint returned data
    result: dict = {"connected": True}
    if email:
        result["email"] = email
    return result


def _parse_usage(data: dict) -> dict:
    result: dict = {}

    for key in ("gpt4RequestsCount", "fast_requests_used", "premiumRequestsCount",
                "requests_used", "used", "requestsCount"):
        if key in data:
            result["requests_used"] = data[key]
            break

    for key in ("gpt4RequestsLimit", "fast_requests_limit", "premiumRequestsLimit",
                "requests_limit", "limit", "requestsLimit"):
        if key in data:
            result["requests_limit"] = data[key]
            break

    if "creditsUsed" in data:
        result["credits_used"] = data["creditsUsed"]
    if "creditsLimit" in data:
        result["credits_limit"] = data["creditsLimit"]

    return result


def _find_cursor_auth() -> tuple[str | None, str | None]:
    token: str | None = None
    email: str | None = None

    db_path = (
        Path.home()
        / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
    )
    if db_path.exists():
        token, email = _read_sqlite(db_path)

    if not token:
        json_path = (
            Path.home()
            / "Library/Application Support/Cursor/User/globalStorage/storage.json"
        )
        if json_path.exists():
            token, email = _read_json(json_path)

    return token, email


def _read_sqlite(db_path: Path) -> tuple[str | None, str | None]:
    token: str | None = None
    email: str | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM ItemTable")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            key: str = row["key"] or ""
            raw = row["value"] or ""

            try:
                val = json.loads(raw)
            except Exception:
                val = raw

            # Exact keys Cursor uses
            if key == "cursorAuth/accessToken":
                if isinstance(val, str) and len(val) > 20:
                    token = val
                continue
            if key == "cursorAuth/cachedEmail":
                if isinstance(val, str) and "@" in val:
                    email = val
                continue

            # Broader fallback
            lkey = key.lower()
            if "cursorauth" in lkey or "cursor/auth" in lkey:
                if isinstance(val, dict):
                    token = token or (
                        val.get("accessToken")
                        or val.get("access_token")
                        or val.get("token")
                    )
                    email = email or val.get("email") or val.get("cachedEmail")
                elif isinstance(val, str) and len(val) > 20:
                    token = token or val

            if not token and "accesstoken" in lkey and isinstance(val, str) and len(val) > 20:
                token = val
            if not email and "email" in lkey and isinstance(val, str) and "@" in val:
                email = val

    except Exception:
        pass

    return token, email


def _read_json(json_path: Path) -> tuple[str | None, str | None]:
    token: str | None = None
    email: str | None = None
    try:
        data = json.loads(json_path.read_text())
        for key, val in data.items():
            lkey = key.lower()
            if "token" in lkey and isinstance(val, str) and len(val) > 20:
                token = token or val
            if "email" in lkey and isinstance(val, str) and "@" in val:
                email = email or val
    except Exception:
        pass
    return token, email
