#!/usr/bin/env bash
# Usage View — one-time setup script for macOS
set -e

echo "==> Checking Python 3..."
python3 --version

echo "==> Installing dependencies..."
pip3 install -r requirements.txt

echo ""
echo "==> Done!  Run the app with:"
echo "    python3 app.py"
echo ""
echo "==> To launch on startup, run:"
echo "    python3 launch_agent.py install"
echo ""
echo "==> API key detection order:"
echo "    Claude  — \$ANTHROPIC_API_KEY  or ~/.claude.json  or ~/.anthropic/api_key"
echo "    Codex   — \$OPENAI_API_KEY     or ~/.codex/auth.json / config.toml"
echo "    Cursor  — read automatically from Cursor's local SQLite store"
echo "              (just make sure you've signed in to Cursor at least once)"
