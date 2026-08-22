# Aura runtime skeleton

Paper-only runtime scaffolding for the future dexter runner. There is no live
order placement, private Kraken API call, systemd unit, or constellation import
in this scaffold. Strategy code is limited to deterministic signal-only brains
until a separate human live gate.

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
  - `run_hard_kill(...)` is the explicit hard-kill escape hatch: it writes
    `hard`, cancels all futures paper orders, and flattens futures paper
    positions without going through `admit()`.
- `runtime.market`
  - Thin OHLCV file spine sourced only from public Kraken Futures Charts HTTPS
    GETs. It stores normalized candles as JSONL for later Ichimoku v0 work.
- `runtime.brain`
  - Deterministic signal-only brains. Ichimoku v0 computes standard 9/26/52
    components from stored OHLCV and emits a discrete `long`/`short`/`flat`
    hypothesis with retunable feature flags.
- `runtime.tools.admit_smoke`
  - Human-triggered smoke entrypoint for CoS; no daemon and no venue call.
- `runtime.tools.supervised_paper`
  - Human-triggered CLI for one supervised Kraken futures-paper order on dexter.
- `runtime.tools.kill_drill`
  - Human-triggered soft/hard/arm/heartbeat/dead-man/drill CLI. No systemd unit
    and no strategy logic.
- `runtime.tools.market_ingest`
  - Human-triggered CLI to pull/status/show futures OHLCV files. No strategy,
    no subprocess Kraken command, and no live trading path.
- `runtime.tools.ichimoku_signal`
  - Human-triggered CLI to compute Ichimoku v0 and append
    `aura.brain_signal.v1` JSONL evidence. The default path never places paper
    orders; `--propose-paper` is explicit and remains dry-run unless
    `--i-understand-paper` is passed.

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
Writing `armed` or deleting the file clears the kill state.

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

## Kill-drill CLI

Soft kill writes `${AURA_ROOT:-/var/aura}/paper/kill_state` and records an ops
event. It does not flatten:

```bash
python3 -m runtime.tools.kill_drill soft
python3 -m runtime.tools.kill_drill drill-a
```

Hard kill is the only admission bypass in the runtime. It is deliberately scoped
to `kraken futures paper ...`, marks events with `kill_override: true`, calls
`cancel-all`, reads positions, and submits opposite-side paper market orders for
open positions:

```bash
python3 -m runtime.tools.kill_drill hard --i-understand-paper
python3 -m runtime.tools.kill_drill drill-b --i-understand-paper
```

Re-arm and heartbeat:

```bash
python3 -m runtime.tools.kill_drill arm
python3 -m runtime.tools.kill_drill heartbeat
python3 -m runtime.tools.kill_drill deadman-check
```

`deadman-check` compares `${AURA_ROOT:-/var/aura}/paper/heartbeat` with
`RiskPolicy.dead_man_seconds` (600 by default). A stale or missing heartbeat
invokes the hard-kill path. This PR only adds the command; no daemon or systemd
timer is installed.

Kill ops events use schema `aura.kill_event.v1` and append under:

```text
${AURA_ROOT:-/var/aura}/evidence/trials/T-kill-.../decision.jsonl
```

Drills can mix `aura.kill_event.v1` ops records and `aura.decision_event.v1`
supervised admission records in the same trial JSONL.

## Market OHLCV spine

The market spine is deterministic file ingest for later brains. It has no
Ichimoku logic, no strategy, no daemon, and no order path. Candles come from the
public Kraken Futures Charts REST endpoint:

```text
GET https://futures.kraken.com/api/charts/v1/trade/{symbol}/{tf}
```

The endpoint path includes `trade` because that is Kraken's chart namespace; it
is not a trade command. The runtime does not call `kraken ohlc` for this spine
and does not invoke any Kraken CLI command while pulling candles.

Default symbol/timeframe:

```text
PF_XBTUSD / 1h
```

`PF_ETHUSD` is available explicitly through `--symbol PF_ETHUSD` or
`--include-eth`. Supported timeframes are `1m`, `5m`, `15m`, `30m`, `1h`, `4h`,
and `1d`.

Files are written under:

```text
${AURA_ROOT:-/var/aura}/market/ohlcv/{SYMBOL}/{tf}.jsonl
${AURA_ROOT:-/var/aura}/market/meta/{SYMBOL}.json
```

Each candle line uses schema `aura.ohlcv_candle.v1`:

```json
{
  "schema": "aura.ohlcv_candle.v1",
  "symbol": "PF_XBTUSD",
  "tf": "1h",
  "ts_ms": 1724284800000,
  "open": "100",
  "high": "101",
  "low": "99",
  "close": "100.5",
  "volume": "12.34",
  "source": "kraken_futures_charts",
  "ingested_at": "2026-08-22T00:00:00Z"
}
```

Pulls upsert by `(symbol, tf, ts_ms)`, rewrite sorted JSONL, and refresh
metadata. Repeated pulls are safe:

```bash
python3.12 -m runtime.tools.market_ingest pull --symbol PF_XBTUSD --tf 1h
python3.12 -m runtime.tools.market_ingest status
python3.12 -m runtime.tools.market_ingest show --symbol PF_XBTUSD --tf 1h --tail 3
```

## Ichimoku v0 brain

Ichimoku v0 is the first explicit mathematical brain. It is signal-only by
default and is a hypothesis for eval, not a claimed edge. The constants are the
standard 9/26/52 settings with a 26-bar displacement:

- Tenkan-sen: midpoint of highest high and lowest low over 9 bars.
- Kijun-sen: midpoint of highest high and lowest low over 26 bars.
- Senkou Span A: midpoint of Tenkan and Kijun, plotted 26 bars ahead.
- Senkou Span B: midpoint of highest high and lowest low over 52 bars, plotted
  26 bars ahead.
- Chikou Span: close plotted 26 bars back.

The latest stored JSONL candle is treated as the latest closed bar. A valid
signal requires at least 78 candles (`senkou_b + displacement`) so the current
cloud can use the displaced span values. The v0 rule is deliberately boring:

- `long`: close is above cloud top, Tenkan > Kijun, and current close is above
  close[t-26].
- `short`: close is below cloud bottom, Tenkan < Kijun, and current close is
  below close[t-26].
- `flat`: anything else.

Compute latest components and bias:

```bash
python3.12 -m runtime.tools.ichimoku_signal compute --symbol PF_XBTUSD --tf 1h
```

Append signal evidence under
`${AURA_ROOT:-/var/aura}/evidence/trials/T-ichi-.../decision.jsonl`:

```bash
python3.12 -m runtime.tools.ichimoku_signal evaluate --symbol PF_XBTUSD --tf 1h
```

That evidence line uses schema `aura.brain_signal.v1` with intent
`brain_signal`, embeds the `aura.ichimoku_signal.v1` payload, and records
component values plus boolean feature flags for later eval retuning.

An optional supervised proposal path exists, but it is off by default and still
goes through `run_supervised_order(...)` and `runtime.risk.admit()`:

```bash
python3.12 -m runtime.tools.ichimoku_signal evaluate \
  --symbol PF_XBTUSD \
  --tf 1h \
  --propose-paper
```

Without `--i-understand-paper`, the proposal path sets `dry_run=True` and never
submits a futures-paper order. `flat` bias is always a no-op. There is no live
scope, no constellation import, no ICT logic, and no daemon.

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
