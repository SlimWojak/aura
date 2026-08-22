# Aura runtime skeleton

Paper-only runtime stubs for the future dexter runner. There is no strategy
logic, live order placement, Kraken API call, systemd unit, or constellation
import in this scaffold.

## Module map

- `runtime.risk`
  - `RiskPolicy` and `load_policy()` mirror the locked ceilings in
    [../RISK_POLICY.md](../RISK_POLICY.md) and `config.example.toml`.
  - `admit(proposal, account_state)` is the pure admission gate future runner
    code must call before any `kraken futures paper ...` order.
- `runtime.evidence`
  - Builds and appends validated decision events to JSONL.
  - Default path: `${AURA_ROOT:-/var/aura}/evidence/trials/{trial_id}/decision.jsonl`.
  - Tests and smoke runs may explicitly write to repo-local
    `evidence/trials/{trial_id}/decision.jsonl`.
- `runtime.tools.admit_smoke`
  - Human-triggered smoke entrypoint for CoS; no daemon and no venue call.

## Risk gate inputs

Minimum proposal fields:

- `symbol`
- `side`
- `size`
- `order_type`
- `notional_usd` or enough data to compute it (`size` + `price_usd`)
- `leverage`
- `client_order_id`

Minimum account state fields:

- `equity`
- `open_positions_count`
- `daily_pnl`
- `weekly_pnl`
- `kill_state` (`armed`, `soft`, or `hard`)
- fresh timestamp as `as_of`, `observed_at`, `state_ts`, or `ts`

Missing or stale account state rejects. Soft/hard kill, oversize notional, max
positions, loss caps, leverage above 2x, or non-`paper_only` mode reject.

## Future runner call pattern

Before any supervised futures-paper CLI order, CoS/delegates should do the
equivalent of:

```python
from runtime.evidence import append_decision_event, build_decision_event
from runtime.risk import admit

admission = admit(proposal, account_state)
event = build_decision_event(
    trial_id=trial_id,
    actor="cos",
    proposal=proposal,
    admission=admission,
)
append_decision_event(event)

if not admission.allowed:
    return admission

# Only future human-triggered runner code reaches this point.
# It may call `kraken futures paper ...` on dexter, never live Kraken.
```

## Smoke usage

From a repo checkout:

```bash
python -m runtime.tools.admit_smoke
python -m runtime.tools.admit_smoke --write
```

`--write` appends dry-run allow/reject events under
`evidence/trials/T-admit-smoke/decision.jsonl` in the repo checkout, not
`/var/aura`.

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
