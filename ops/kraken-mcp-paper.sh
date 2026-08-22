#!/usr/bin/env bash
# Aura paper-only MCP — NEVER widen -s without Slim go.
set -euo pipefail
source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
exec kraken mcp -s market,paper,futures-paper "$@"
