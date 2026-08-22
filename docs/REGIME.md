# Aura Regime Phase 1

Aura Regime Phase 1 is the production permissioning spine for labeling market
structure before any future paper runner asks Risk/Ops for admission. It is a
pure, paper-only classifier under `runtime/regime/`: no order path, no live
Kraken scope, no constellation coupling, and no cartridge eval wiring.

Charter context remains [AURA_CHARTER.md](AURA_CHARTER.md). Build-plan context
is [BUILD_PLAN.md](BUILD_PLAN.md).

## Non-goals

- No `admit()` hard veto integration yet; that is Phase 2.
- No entry strategy and no paper order proposal.
- No PnL claim. Phase 1 fitness is label stability, occupancy, and flip rate.
- No funding/open-interest, RSI/KAMA, parameter zoo, Pine, or live trading.
- No Research Intern cartridge replacement. The ADX/ER/thickness cartridge
  gates remain separate research ammo and are not wired into this module.

## States

The state set is exactly:

- `TREND_BULL`
- `TREND_BEAR`
- `TRANSITION`
- `RANGE`
- `VOLATILE`

`RegimeSnapshot` records `{state, confidence, reasons[], features{}, as_of, tf}`
and serializes as `aura.regime_label.v1`.

## Defaults

The frozen defaults live in `runtime.regime.types.RegimeParams` and are mirrored
for review in `runtime/regime/defaults.yaml`:

- Ichimoku 9/26/52 with displacement 26.
- Regime timeframe `4h`, resampled from stored `1h` OHLCV.
- Optional higher-timeframe veto `1d`.
- ADX period 14, `adx_weak=20`, `adx_strong=25`.
- `thin_kumo_atr=0.4`.
- Span-B/Kijun/Tenkan flatness over `flat_n=8` bars using a small ATR fraction.
- Dwell `3` closed regime bars before state changes.

Price-vs-kumo always uses displaced spans under the current bar:
`spanA[t-displacement]` and `spanB[t-displacement]`. The classifier never uses
undisplaced raw spans for current price location.

## Classification precedence

Classification is deterministic:

1. `TREND_BULL` / `TREND_BEAR` only when the full stack holds.
2. `TRANSITION` on future kumo twist or higher-timeframe disagreement.
3. `RANGE` on explicit range structure.
4. `VOLATILE` when price is outside the kumo without trend agreement.
5. `TRANSITION` fail-closed if no rule matches or required features are missing.

### Trend stack

`TREND_BULL` requires all of:

- close above displaced kumo top;
- Tenkan > Kijun;
- current close > close[t-displacement] Chikou proxy;
- ADX >= `adx_strong` and +DI > -DI;
- displaced kumo width / ATR >= `thin_kumo_atr`;
- not breaking into a long flat Senkou Span B run;
- if daily HTF is provided, daily price is not below daily kumo.

`TREND_BEAR` mirrors the same checks in the bearish direction.

### Range and volatility

`RANGE` fires when price is inside the kumo, or the kumo is thin while ADX is
weak, or both Tenkan and Kijun are flat.

`VOLATILE` fires when price is outside the kumo but ADX is below `adx_strong`,
TK alignment opposes location, or DI disagrees with location.

`TRANSITION` covers known future cloud twists, HTF/LTF disagreement, dwell
pending after price just left the kumo, and fail-closed missing features.

## CLI labeler

The CLI reads stored 1h OHLCV and writes labels plus summary evidence:

```bash
cd ~/aura && export AURA_ROOT=/var/aura
python3.12 -m runtime.tools.regime_label label --symbol PF_XBTUSD --tf 4h --htf 1d
```

Input:

```text
${AURA_ROOT:-/var/aura}/market/ohlcv/{SYMBOL}/1h.jsonl
```

Output:

```text
${AURA_ROOT:-/var/aura}/evidence/regimes/R-.../labels.jsonl
${AURA_ROOT:-/var/aura}/evidence/regimes/R-.../summary.json
```

The printed summary includes occupancy percentages and flip rate. These are
label-quality diagnostics only; they are not strategy returns.
