"""
Claude provider — shows subscription status.

API key validation is disabled for now; will be added later for usage stats.
"""


def get_claude_status() -> dict:
    return {"connected": True, "plan": "Pro"}
