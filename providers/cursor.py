"""
Cursor provider — shows subscription status.

API token validation is disabled for now; will be added later for usage stats.
"""


def get_cursor_usage() -> dict:
    return {"connected": True}
