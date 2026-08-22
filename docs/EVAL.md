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

Single cartridge eval with return stats and DSR trial count:

```bash
python -m runtime.tools.eval_run cartridge \
  --aura-root /var/aura \
  --id ichi_params_20_60_trend_v0 \
  --symbol PF_XBTUSD \
  --tf 1h \
  --fee-bps 4 \
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
  --regime-tf 4h \
  --regime-htf 1d \
  --oos-split 0.7 \
  --atr-period 14 \
  --trial-count 34 \
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

## Phase 2 regime ablations

The Phase 2 ablation cartridges in `docs/REGIME.md` are draft-only eval
experiments. Run all twelve PF_XBTUSD/PF_ETHUSD cartridges with forced 70/30
fee-on OOS and `--trial-count 12`; AB-0 omits the Phase 2 gate, while AB-FULL
and each single-component removal use `--regime-tf 4h --regime-htf 1d`.

Use ATR-normalized return stats for the decision memo. A component earns its
place only if removing it materially worsens ATR Calmar/MAR or DSR on both
symbols versus AB-FULL. Do not mutate cartridge statuses from these draft runs.

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
