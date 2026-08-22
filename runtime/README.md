# Aura runtime skeleton

This directory is reserved for future paper-runtime components. Nothing here is
implemented yet, and no strategy logic belongs in this scaffold.

## Intended components

- **Paper runner:** supervised Kraken paper execution loop after CoS and Slim
  approve the runbook gates.
- **Risk daemon:** script-heavy admission layer for order limits, loss caps,
  leverage caps, kill states, and dead-man behavior.
- **Scribe:** converts decision events and runtime logs into evidence artifacts,
  daily one-pagers, weekly memos, and drill records.

## Boundaries

- Mode is paper-only.
- `AURA_ROOT` is `/var/aura` on dexter.
- Spot paper MCP is `kraken mcp -s market,paper`.
- Futures paper is CLI-only on dexter.
- Live scopes and constellation imports are forbidden.

See:

- [../AGENTS.md](../AGENTS.md)
- [../RISK_POLICY.md](../RISK_POLICY.md)
- [../ops/kraken_scopes.md](../ops/kraken_scopes.md)
- [../docs/DISPATCH.md](../docs/DISPATCH.md)
