#!/usr/bin/env bash
# Aura paper-only MCP for kraken-cli 0.4.1
# NOTE: MCP service "futures-paper" does NOT exist in 0.4.1.
# Futures paper is CLI-only: `kraken futures paper ...`
# Never add: trade | futures | funding | earn | subaccount | all | --allow-dangerous
set -euo pipefail
source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
exec kraken mcp -s market,paper "$@"
