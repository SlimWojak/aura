# Aura brain-change sequence lock

Date: 2026-08-22

Scope: paper-only `SlimWojak/aura`. This brief locks the next research order; it
does not record run results, mutate cartridge YAML, or authorize a runner.

## Locked sequence

1. **Run the per-bar IC / feature screen first.**
   - Use stored BTC+ETH 1h OHLCV:
     `PF_XBTUSD`, `PF_ETHUSD`, `--tf 1h`.
   - Default horizons: 4/12/24/48 forward bars.
   - Forward return target:
     `(close[t+h] - close[t]) / ATR[t]`.
   - Evidence path pattern:
     `/var/aura/evidence/evals/ic-screen-YYYYMMDD/`.
   - Command:
     ```bash
     python -m runtime.tools.eval_run ic-screen \
       --aura-root /var/aura \
       --symbols PF_XBTUSD,PF_ETHUSD \
       --tf 1h \
       --horizons 4,12,24,48 \
       --atr-period 14 \
       --output-id ic-screen-20260822
     ```
   - Output artifacts: `report.json`, `scores.csv`, `SUMMARY.md`.
   - CIs use Newey-West/HAC for overlapping forward returns.
   - Benjamini-Hochberg q-values are reported across emitted feature tests.
   - Feature kill rule: a feature whose usable CIs span 0 on both symbols is a
     dead feature.

2. **Only after the IC screen, compare survivor-derived 15m impulse-under-TREND
   against `vol-event@1h`.**
   - The comparison must be pre-registered from screen survivors.
   - No 15m ingest is part of the IC-screen PR.
   - No dead IC feature gets a Track A bake-off.

## Refusals / freezes

- Intern remains frozen.
- Do not run blind R8 cartridge generation.
- Do not loosen Track A.
- Do not revive killed cartridges.
- Refuse 5m ungated experiments.
- Refuse an Ichimoku polish zoo.
- Refuse Track A loosening or treating a screen survivor as a keep.
- Keep all work paper-only: no live Kraken scopes, no live keys, no funding,
  earn, subaccount, transfer, or withdrawal paths.

## Look-ahead fence

Cloud features must use only values known at bar `t`: displaced Senkou spans
under the current bar come from raw spans at `t-displacement`. Chikou-style
features must compare current close with past reference values such as
`close[t-displacement]`; chart-displaced future Chikou values are not admissible.

## Reviewer interpretation

The IC screen is a disposal filter. It can kill dead features before Track A
spend; it cannot promote a strategy, change production spine defaults, or unlock
runtime authority.
