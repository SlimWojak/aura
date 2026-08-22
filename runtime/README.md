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
- `runtime.runner`
  - `run_supervised_order(...)` implements the first real CoS paper loop:
    human trigger -> live futures-paper state -> `admit()` -> decision JSONL
    -> optional futures-paper order.
- `runtime.tools.admit_smoke`
  - Human-triggered smoke entrypoint for CoS; no daemon and no venue call.
- `runtime.tools.supervised_paper`
  - Human-triggered CLI for one supervised Kraken futures-paper order on dexter.

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

## Supervised futures-paper loop

There is now one thin, human-triggered paper runner. It is not a daemon, has no
systemd unit, and contains no strategy logic:

```bash
python -m runtime.tools.supervised_paper \
  --trial-id T-cos-loop-001 \
  --symbol PF_XBTUSD \
  --side buy \
  --size 0.001 \
  --leverage 2 \
  --client-order-id aura-cos-001 \
  --notional-usd 100
```

The runner reads live futures-paper state from dexter before every admission:

```text
kraken futures paper status -o json
kraken futures paper positions -o json
```

It maps that state into `admit()` as `equity`, `open_positions_count`,
`daily_pnl`, `weekly_pnl`, `kill_state`, and a fresh UTC `as_of`. `daily_pnl`
uses a real status PnL field when present. `weekly_pnl` uses a real weekly field
when present; if no honest weekly field is available, the runner fails closed by
leaving it unavailable for `admit()` and records the mapping reason in JSONL.
For market orders, order notional must be supplied with `--notional-usd`; if it
is missing, `admit()` rejects rather than inventing a price.

Evidence defaults to:

```text
${AURA_ROOT:-/var/aura}/evidence/trials/{trial_id}/decision.jsonl
```

`--aura-root` exists for unit tests and supervised local smoke only. Production
on dexter should use `/var/aura`. A kill file at
`/var/aura/paper/kill_state` containing `soft` or `hard` rejects new entries.

Dry run admits and writes intent evidence without any venue order call:

```bash
python -m runtime.tools.supervised_paper \
  --trial-id T-cos-loop-001-dry \
  --symbol PF_XBTUSD \
  --side buy \
  --size 0.001 \
  --leverage 2 \
  --client-order-id aura-cos-001-dry \
  --notional-usd 100 \
  --dry-run
```

For allowed non-dry-run orders, the only venue command shape is futures paper:

```text
kraken futures paper buy|sell SYMBOL SIZE --type market --client-order-id ID -o json
```

The default size example, `0.001` XBT, is intentionally tiny and well below the
locked USD 500 notional cap when paired with a truthful small notional such as
`--notional-usd 100`. The gate still enforces USD 500 max notional, 2x leverage,
2 open positions, daily/weekly loss caps, kill state, and fresh account state.

## Runner call pattern

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

if not admission.allowed:
    event["venue"]["response"] = {"not_called": True, "reason": "risk_gate_reject"}
    append_decision_event(event)
    return admission

# Only human-triggered runner code reaches this point.
# It may call `kraken futures paper ...` on dexter, never live Kraken.
response = submit_futures_paper_order(proposal)
event["venue"]["response"] = response
append_decision_event(event)
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
