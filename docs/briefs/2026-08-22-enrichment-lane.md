# Aura enrichment lane lock - 2026-08-22

## Fence

This lane is Aura-native and paper-only. It may read stored OHLCV under the Aura
market store and write reviewable repo/evidence artifacts. It must not import,
vendor, submodule, or write constellation, ATOM, RIVER clinical, live Kraken, or
runtime secret paths.

No live trading scopes, no Intern unlock, no killed-id revival, no lower-timeframe
ADDR, no Track A loosening, and no cartridge mill are in scope. The IC screen
comes before any cartridge proposal.

## Locked ranking

Binding order for enrichment candidates:

1. Chikou cleared of HTF Daily dealing-range / swing structure.
2. Daily FVG overlap with flat Senkou Span B as a veto/confirm feature, not a
   full ICT stack.
3. Daily dealing-range premium/discount as a hard side gate.

Parked and out of this PR: ADDR, lower-timeframe dealing ranges, RSI divergence,
Volume Profile POC. Intern remains frozen.

## Thin definitions registered for IC screening

All definitions are computed from stored OHLCV only and are aligned to the
decision bar with higher-timeframe close confirmation.

### Daily dealing range

Source: daily candles, or complete daily candles resampled from stored 1h OHLCV.

Definition:

- A daily swing high at candle `j` is confirmed only after candle `j+1` closes
  and requires `high[j] > high[j-1]` and `high[j] > high[j+1]`.
- A daily swing low is symmetric: `low[j] < low[j-1]` and
  `low[j] < low[j+1]`.
- The active Daily DR is the latest confirmed swing high paired with the latest
  confirmed swing low. If either side is missing, same-candle, or inverted, the
  feature is missing.
- `daily_dr_side` is `premium` when close is above the midpoint, `discount` when
  below, and `equilibrium` exactly at the midpoint.
- `daily_dr_position` is continuous: low = `-1`, midpoint = `0`, high = `+1`;
  values outside the range may exceed `abs(1)`.

### Chikou clears Daily DR

For bar `t`, use the existing Ichimoku displacement. The Chikou reference bar is
`t - displacement`. The feature compares `close[t]` with the Daily DR that was
known at the reference bar, not with future daily structure.

- `chikou_clears_daily_dr` is true when `close[t]` is above that DR high or below
  that DR low.
- `chikou_daily_dr_clearance_atr` is signed ATR-normalized clearance beyond the
  relevant DR edge, or `0` when still inside the range.

### Daily FVG and flat Span B overlap

Source: latest confirmed daily 3-candle fair value gap.

Definition:

- Bullish FVG at candle `i`: `low[i] > high[i-2]`; gap bounds are
  `[high[i-2], low[i]]`.
- Bearish FVG at candle `i`: `high[i] < low[i-2]`; gap bounds are
  `[high[i], low[i-2]]`.
- `daily_fvg_side` is `bullish`, `bearish`, or `none`.
- `daily_fvg_price_inside` is true when close is inside the latest gap.
- `daily_fvg_distance_atr` is distance from close to the nearest gap edge,
  ATR-normalized, and `0` inside the gap.
- `fvg_flat_spanb_overlap` is true when the existing lookahead-safe displaced
  Senkou Span B under bar `t` is flat for `flat_n` bars and lies inside the
  latest daily FVG.

This is a thin overlap/veto-confirm feature only. It is not a full ICT stack.

## IC-screen command

Run enrichment-only IC on the default BTC+ETH 1h Aura stores:

```bash
python -m runtime.tools.eval_run ic-screen \
  --aura-root /var/aura \
  --symbols PF_XBTUSD,PF_ETHUSD \
  --tf 1h \
  --horizons 4,12,24,48 \
  --atr-period 14 \
  --feature-set enrichment \
  --output-id ic-screen-enrichment-20260822
```

The output uses the existing IC-screen contract: forward ATR-normalized returns,
Newey-West/HAC CIs for overlapping horizons, Benjamini-Hochberg q-values, and
the same two-symbol kill summary. It does not mutate cartridges, unlock Intern,
revive killed ids, or change Track A.
