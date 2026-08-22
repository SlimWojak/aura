#!/usr/bin/env bash
# Read-only dexter smoke helper for Aura paper runtime checks.
# Run from a trusted CoS console with SSH access to dexter.

set -euo pipefail

DEXTER_HOST="${DEXTER_HOST:-dexter}"
AURA_ROOT="${AURA_ROOT:-/var/aura}"

ssh "$DEXTER_HOST" bash -s -- "$AURA_ROOT" <<'REMOTE'
set -euo pipefail

AURA_ROOT="$1"

echo "== aura root =="
printf '%s\n' "${AURA_ROOT:-/var/aura}"

echo
echo "== kraken version =="
kraken --version

echo
echo "== spot paper/mcp scope reminder =="
printf '%s\n' "MCP scope must be: kraken mcp -s market,paper"

echo
echo "== futures paper status =="
kraken futures paper status

echo
echo "== futures paper positions =="
kraken futures paper positions
REMOTE
