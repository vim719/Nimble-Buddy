#!/usr/bin/env bash
# Share the locally running NimbleBuddy over a temporary public HTTPS URL
# using a free Cloudflare Quick Tunnel (no account, no API key).
#
# Usage:
#   1. Start the app:   ./venv/bin/uvicorn app.main:app --port 8000
#   2. In a new tab:    ./scripts/share.sh            (or PORT=8080 ./scripts/share.sh)
#   3. Share the https://<random>.trycloudflare.com URL it prints. Ctrl+C to stop sharing.
set -euo pipefail

PORT="${PORT:-8000}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed."
  echo "  macOS:   brew install cloudflared"
  echo "  Other:   https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi

if ! curl -fsS "http://localhost:${PORT}/api/status" >/dev/null 2>&1; then
  echo "NimbleBuddy is not running on port ${PORT}. Start it first:"
  echo "  ./venv/bin/uvicorn app.main:app --port ${PORT}"
  exit 1
fi

echo "NimbleBuddy status: $(curl -fsS "http://localhost:${PORT}/api/status")"
echo
echo "Starting Cloudflare Quick Tunnel. Look for the https://*.trycloudflare.com URL below."
echo "Anyone with the URL can use your Nimble credits and Groq quota. Press Ctrl+C to stop sharing."
echo

exec cloudflared tunnel --no-autoupdate --url "http://localhost:${PORT}"
