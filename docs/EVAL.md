# Aura eval harness

Aura evals are paper-only. The harness reads stored OHLCV and paper evidence
under `AURA_ROOT` and writes reviewable artifacts under
`$AURA_ROOT/evidence/evals`; it does not call live Kraken scopes or mutate
cartridge status.

## Return layers

Existing point-PnL metrics remain in `metrics.total_pnl_points`,
`metrics.max_drawdown_points`, and fee-adjusted point fields for ledger
continuity. Track A adds two return streams to each backtest report:

- `simple_returns`: one-unit position PnL divided by the prior mark price,
  compounded for total return and drawdown.
- `atr_normalized_returns`: one-unit position PnL divided by prior-bar Wilder
  ATR, treated as an additive unit-risk path. This is the preferred metric for
  comparing BTC/ETH and compressed/high-volatility regimes.

Per-bar rows are persisted in both `report.json` under `return_series.series`
and a sibling `returns.jsonl`. Rows include gross and net simple returns, gross
and net ATR-normalized returns, point PnL, fee drag, ATR, position side, bar
index, and timestamp.

Fees remain the same point-fee model as the old harness:

```text
fee_points = fee_bps / 10000 * (entry_price + exit_price)
```

The return layer allocates fee drag on the exit row in both simple and
ATR-normalized units.

Funding is optional and off by default. When `--apply-funding` is set, evals
load `$AURA_ROOT/market/funding/{SYMBOL}.jsonl` and apply the stored
`relative_funding_rate` to held bars as a return-series cashflow, not as an
entry gate, regime gate, cartridge status change, or runner/live cashflow:

```text
signed_funding_return = -position_sign * relative_funding_rate
funding_points = signed_funding_return * mark
funding_atr_normalized_return = funding_points / ATR
net_return = gross_return - fee_drag + signed_funding_return
```

The sign follows Kraken futures convention: a positive relative funding rate
means longs pay and shorts receive. A long held through positive relative
funding has lower net returns; a short receives the same amount. Summary
`funding_drag_*` fields are reported as drag, so a funding benefit appears as a
negative drag.

Funding accrues on every held bar. This differs from fees, which remain
exit-row only. Alignment is by candle open timestamp (`ts_ms`): a 1h candle uses
the funding row labeled with that candle's open, and a 4h candle sums completed
hourly funding labels with `ts` in `[bar_open, bar_close)`. The next hour's
label is never used for the current bar.

Stored funding coverage on dexter currently starts around 2025-08-20 while some
OHLCV spans begin in 2023. With `--apply-funding`, missing funding on any held
bar in the scored window fails closed with `funding_missing_held_bars=...`.
Either use `--since` inside the stored funding span or run an explicit stress
test with `--funding-bps`, a constant hourly relative funding assumption in bps.
`--funding-bps` is mutually exclusive with stored rates and does not overload
`--fee-bps`.

## Track C exit modes

The cartridge eval path supports closed-bar paper exits beyond `bias_flip`:

- `kijun_trail`: long exits when close < current Kijun; short mirrors above
  Kijun.
- `atr_stop`: static stop initialized from the entry decision bar ATR and paper
  entry price.
- `chandelier_trail`: tighten-only ATR Chandelier line using the highest high or
  lowest low available through the evaluated bar.

These modes keep the harness paper-only and preserve the existing execution
assumption: a closed-bar trigger exits at next open when available, otherwise
current close. Missing Kijun/ATR/Chandelier inputs fail closed by blocking the
new paper entry rather than running an unprotected trade. `kill_criteria` can use
`baseline_metric: atr_normalized_total_return` to compare candidates against the
same Track A return layer.

## Per-trial statistics

Each return stream emits:

- annualized Sharpe from per-bar mean/std and timeframe-derived periods/year;
- Lo-style autocorrelation variance inflation and annualized Sharpe standard
  error using up to 12 return lags;
- Probabilistic Sharpe Ratio (PSR) versus SR=0;
- Deflated Sharpe Ratio (DSR), using `--trial-count` as the honest count of
  tried variants;
- skew, raw kurtosis, excess kurtosis;
- max drawdown in return space;
- Calmar/MAR;
- trade count, average holding bars, turnover, and fee drag in return terms.

DSR is only meaningful when `--trial-count` counts every parameter variant that
was tried, including variants later killed or omitted from a short report set.
If omitted on a single eval run it defaults to `1`, which means no multiple-test
deflation beyond PSR.

## CLI examples

Per-bar Ichimoku/regime IC feature screen on the default BTC+ETH 1h stores:

```bash
python -m runtime.tools.eval_run ic-screen \
  --aura-root /var/aura \
  --symbols PF_XBTUSD,PF_ETHUSD \
  --tf 1h \
  --horizons 4,12,24,48 \
  --atr-period 14 \
  --output-id ic-screen-20260822
```

The screen reads `${AURA_ROOT}/market/ohlcv/{PF_XBTUSD,PF_ETHUSD}/1h.jsonl`
and writes:

```text
${AURA_ROOT}/evidence/evals/ic-screen-YYYYMMDD/report.json
${AURA_ROOT}/evidence/evals/ic-screen-YYYYMMDD/scores.csv
${AURA_ROOT}/evidence/evals/ic-screen-YYYYMMDD/SUMMARY.md
```

It is bar-level feature screening, not a trade backtest. Forward returns are
`(close[t+h] - close[t]) / ATR[t]` for horizons 4/12/24/48. Continuous features
are scored by Pearson IC. Categorical features, including the five regime states
and `cloud_bias in {-1,0,+1}`, are scored as conditional mean forward
ATR-normalized returns. Overlapping forward returns use Newey-West/HAC
Bartlett-lag CIs with `lag=min(horizon, n-1)`. Benjamini-Hochberg q-values are
computed across emitted symbol x feature/level x horizon tests.

Look-ahead fence: cloud features use the displaced cloud values under bar `t`
from raw spans at `t-displacement`; Chikou gap uses
`close[t] - close[t-displacement]`. The chart-displaced future Chikou value is
not used.

Kill rule in the summary: a feature is dead when every usable CI for both
PF_XBTUSD and PF_ETHUSD spans 0. Survivors are only later bake-off candidates;
the IC screen does not mutate cartridge YAML, unlock Intern, or loosen Track A.

Single cartridge eval with return stats and DSR trial count:

```bash
python -m runtime.tools.eval_run cartridge \
  --aura-root /var/aura \
  --id ichi_params_20_60_trend_v0 \
  --symbol PF_XBTUSD \
  --tf 1h \
  --fee-bps 4 \
  --apply-funding \
  --regime-tf 4h \
  --regime-htf 1d \
  --atr-period 14 \
  --trial-count 34 \
  --metrics-only
```

Chronological IS/OOS eval with the same return stats:

```bash
python -m runtime.tools.eval_run cartridge \
  --aura-root /var/aura \
  --id ichi_params_20_60_trend_v0 \
  --symbol PF_ETHUSD \
  --tf 1h \
  --fee-bps 4 \
  --apply-funding \
  --regime-tf 4h \
  --regime-htf 1d \
  --oos-split 0.7 \
  --atr-period 14 \
  --trial-count 34 \
  --metrics-only
```

Constant hourly funding stress, without reading stored funding rates:

```bash
python -m runtime.tools.eval_run backtest \
  --aura-root /var/aura \
  --symbol PF_XBTUSD \
  --tf 1h \
  --apply-funding \
  --funding-bps 1 \
  --metrics-only
```

Score a directory of saved reports for matrix DSR and PBO:

```bash
python -m runtime.tools.eval_run matrix \
  --reports-dir /var/aura/evidence/evals \
  --metric atr_normalized \
  --trial-count 34 \
  --cscv-groups 8
```

`--metric simple` is available for a percent-return matrix, but keep decisions
should use the same normalized metric across candidate and baseline rows.

Synthetic positive/negative controls for Track A live in
[`docs/POWER_TEST.md`](POWER_TEST.md) and run with:

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

## Phase 2 regime ablations

The Phase 2 ablation cartridges in `docs/REGIME.md` are draft-only eval
experiments. Run all twelve PF_XBTUSD/PF_ETHUSD cartridges with forced 70/30
fee-on OOS and `--trial-count 12`; AB-0 omits the Phase 2 gate, while AB-FULL
and each single-component removal use `--regime-tf 4h --regime-htf 1d`.

Use ATR-normalized return stats for the decision memo. A component earns its
place only if removing it materially worsens ATR Calmar/MAR or DSR on both
symbols versus AB-FULL. Do not mutate cartridge statuses from these draft runs.

After the banked ablation and Slim lock, omitted `phase2_ablation` metadata no
longer implies the old all-on stack. With `--regime-tf`/`--regime-htf`, the
paper eval default is the thinned production spine: HTF veto and kumo width/ATR
on, ADX/DI and dwell/hysteresis off. Use explicit AB-FULL cartridges when an
eval needs to reconstruct the old all-on component stack.

## PBO / CSCV v0

The `matrix` command loads saved `report.json` files containing
`return_series.series`, aligns by truncating all trials to the shortest return
count, and computes Probability of Backtest Overfitting with Combinatorially
Symmetric Cross-Validation:

1. Split the chronological return path into an even number of groups
   (`--cscv-groups`, default `8`).
2. For every combination of half the groups as in-sample, use the complement as
   out-of-sample.
3. Pick the best in-sample trial by Sharpe.
4. Rank that trial's out-of-sample Sharpe among all trials.
5. Count the split as overfit when the selected trial ranks in the bottom half
   out of sample.

Optional `--purge-groups` and `--embargo-groups` remove in-sample groups around
or after OOS groups when a trial design needs leakage controls. This v0 ships
CSCV/PBO. A later CPCV path can reuse the saved `returns.jsonl` rows and add
event-horizon-aware purge/embargo for CPCV `N=8, k=2` style paths.

## Intended keep gate

The gate is documented but not wired as a hard fail:

```text
DSR > 0.95
AND PBO < 0.10
AND beats baseline on the same normalized metric on BOTH PF_XBTUSD and PF_ETHUSD
```

The current provisional keep `ichi_params_20_60_trend_v0` already fails the
both-symbols requirement in the banked ledger: BTC passed the older OOS gate,
but ETH OOS failed and stayed a paper-only provisional keep. CoS should re-score
that id on dexter with the commands above before making any new keep decision.
The first Track A rescore is now banked in `docs/LEDGER.md` as a provisional-fail
while the cartridge YAML remains a provisional paper keep.

## Re-scoring the ledger

This PR does not re-score historical cartridges. After merge, CoS can run the
cartridge command for each saved trial/symbol pair on dexter, then run the
matrix command over the resulting eval directories. Keep the `--trial-count`
value anchored to the full tried-variant count for the bank, not the number of
reports selected for review.
