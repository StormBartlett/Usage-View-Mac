"""
Cursor provider — reads the auth token from Cursor's local SQLite store
then queries the Cursor usage API.

Token location (macOS):
  ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
  Table: ItemTable, key contains 'cursorAuth'

Fallback: storage.json in the same directory.
"""
import json
import os
import sqlite3
from pathlib import Path

import requests

TIMEOUT = 8

# Cursor stores its backend data at api2.cursor.sh
USAGE_ENDPOINTS = [
    "https://www.cursor.com/api/usage",
    "https://api2.cursor.sh/auth/usage",
    "https://api2.cursor.sh/usage",
]


def get_cursor_usage() -> dict:
    token, email = _find_cursor_auth()

    if not token:
        return {"connected": False, "error": "no auth token found — open Cursor first"}

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
                return {"connected": False, "error": "token expired — reopen Cursor IDE app"}
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            return {"connected": False, "error": "no internet"}
        except Exception:
            continue

    # Token found but no usage endpoint worked — still show connected
    result: dict = {"connected": True}
    if email:
        result["email"] = email
    return result


# ---------------------------------------------------------------------------
# Response parsing — handles different shapes Cursor has used over time
# ---------------------------------------------------------------------------

def _parse_usage(data: dict) -> dict:
    result: dict = {}

    # Fast / premium requests (old model)
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

    # Credit-based billing (newer model: credits in USD cents or dollars)
    if "creditsUsed" in data:
        result["credits_used"] = data["creditsUsed"]
    if "creditsLimit" in data:
        result["credits_limit"] = data["creditsLimit"]

    return result


# ---------------------------------------------------------------------------
# Auth token discovery
# ---------------------------------------------------------------------------

def _find_cursor_auth() -> tuple[str | None, str | None]:
    token: str | None = None
    email: str | None = None

    # --- Primary: SQLite state.vscdb ---
    db_path = (
        Path.home()
        / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
    )
    if db_path.exists():
        token, email = _read_sqlite(db_path)

    # --- Fallback: storage.json ---
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
        # Open read-only
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM ItemTable")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            key: str = row["key"] or ""
            raw = row["value"] or ""

            # Parse JSON value where possible
            try:
                val = json.loads(raw)
            except Exception:
                val = raw

            lkey = key.lower()

            # Exact keys Cursor uses (checked against observed DB contents):
            #   "cursorAuth/accessToken"
            #   "cursorAuth/cachedEmail"
            #   "cursorAuth/stripeMembershipType"
            if key == "cursorAuth/accessToken":
                if isinstance(val, str) and len(val) > 20:
                    token = val
                continue

            if key == "cursorAuth/cachedEmail":
                if isinstance(val, str) and "@" in val:
                    email = val
                continue

            # Broader fuzzy fallback for future key name changes
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
