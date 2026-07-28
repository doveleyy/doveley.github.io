#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${1:-8000}"
URL="http://127.0.0.1:${PORT}/index.html"

echo "Serving TME visual prototypes at:"
echo "  ${URL}"
echo
echo "Press Ctrl+C to stop the server."

python3 -m http.server "${PORT}" --bind 127.0.0.1
