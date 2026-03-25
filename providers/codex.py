"""
Codex / OpenAI provider — shows subscription status.

API key validation is disabled for now; will be added later for usage stats.
"""


def get_codex_usage() -> dict:
    return {"connected": True}
