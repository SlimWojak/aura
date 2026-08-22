# Track A synthetic-edge power test

This harness is a paper-only positive/negative control for the Track A eval
gate:

```text
DSR > 0.95
AND PBO < 0.10
AND beats baseline on the same normalized metric on BOTH PF_XBTUSD and PF_ETHUSD
```

It answers one narrow question: can the current DSR/PBO machinery keep a known
synthetic edge and reject a no-edge shuffled control? It does not change
cartridge statuses, place orders, access live Kraken scopes, or promote any
strategy.

## Entry point

```bash
python -m runtime.tools.power_test --positive \
  --aura-root /var/aura \
  --symbol PF_XBTUSD \
  --tf 1h \
  --fee-bps 4 \
  --oos-split 0.7 \
  --trial-count 37 \
  --atr-period 14 \
  --regime-tf 4h \
  --regime-htf 1d
```

Run the negative control with the same flags:

```bash
python -m runtime.tools.power_test --negative \
  --aura-root /var/aura \
  --symbol PF_XBTUSD \
  --tf 1h \
  --fee-bps 4 \
  --oos-split 0.7 \
  --trial-count 37 \
  --atr-period 14 \
  --regime-tf 4h \
  --regime-htf 1d
```

Repeat both commands for `PF_ETHUSD`. The CLI writes artifacts under
`/var/aura/evidence/power_tests/...` by default:

- `summary.json` for the power-test verdict;
- one synthetic eval `report.json` per honest path under `reports/<trial-id>/`;
- sibling `returns.jsonl` files written by the normal eval report writer.

Use `--output-dir` to place artifacts elsewhere.

## What the controls do

The clean injection point is `return_series.series[*].net_atr_normalized_return`.
The power test first reads stored OHLCV for the requested symbol/timeframe, then
builds ATR-normalized close-to-close noise from the OOS segment selected by
`--oos-split`.

- **Positive control**: writes one `positive-edge` path with a synthetic
  period-level ATR-normalized Sharpe (`--edge-sharpe`, default `0.9`) and
  `N_honest = --trial-count` deflation. The remaining paths are null
  distractors. The selected edge must clear DSR and PBO.
- **Negative control**: block-shuffles and de-means ATR-normalized return blocks
  (`--block-size`, default `24`) so the synthetic edge is absent. The run passes
  only if Track A does **not** keep the best shuffled path.

The `--regime-tf` and `--regime-htf` flags are accepted for command parity with
thin-spine evals, but the injection happens after strategy/regime logic at the
return-series level.

## Pass/fail

The CLI exits `0` when the control behaves as expected:

- positive control: `track_a_keep: true`, selected trial DSR > `0.95`, PBO <
  `0.10`;
- negative control: `track_a_keep: false`.

The JSON includes both:

- `n_paths`: runnable synthetic paths written and scored by PBO;
- `n_honest`: the honest tried-variant count used for DSR deflation.

This makes the old PBO scar explicit: PBO v0 only sees runnable saved paths,
while DSR must be deflated by the full honest search count.

## What this does not prove

- It is not evidence that any Aura cartridge has an edge.
- It does not validate live trading, live keys, funding, earn, withdrawals, or
  subaccounts.
- It does not model slippage, fill quality, or trade turnover. `--fee-bps` is
  recorded for eval parity; the synthetic return stream is treated as already
  post-fee.
- It does not prove that annualized 1h Sharpe near 1.0 can clear DSR 0.95 at
  `N_honest=37`. With the current DSR formula that would require much more
  sample than the recent Track A bars provide. This harness labels its injected
  edge as period-level ATR-normalized Sharpe and reports annualized Sharpe in
  the generated matrix for visibility.
