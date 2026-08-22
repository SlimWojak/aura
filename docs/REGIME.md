# Aura Regime Phase 1/2

Aura Regime Phase 1 is the production permissioning spine for labeling market
structure before any future paper runner asks Risk/Ops for admission. It is a
pure, paper-only classifier under `runtime/regime/`: no order path, no live
Kraken scope, no constellation coupling, and no cartridge eval wiring.

Charter context remains [AURA_CHARTER.md](AURA_CHARTER.md). Build-plan context
is [BUILD_PLAN.md](BUILD_PLAN.md).

## Non-goals

- No entry strategy and no paper order proposal.
- No PnL claim from labels alone. Phase 1 fitness is label stability,
  occupancy, and flip rate; Phase 2 evals remain paper-only comparisons.
- No funding/open-interest, RSI/KAMA, parameter zoo, Pine, or live trading.
- No Research Intern cartridge replacement. The ADX/ER/thickness cartridge
  gates remain separate research ammo.

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

## Phase 2 hard veto

Phase 2 wires regime labels into paper entry paths as a hard permissioning veto:

- `TREND_BULL` allows new `long` entries only.
- `TREND_BEAR` allows new `short` entries only.
- `RANGE`, `VOLATILE`, and `TRANSITION` deny all new entries.
- Missing or unknown state fails closed with `regime_veto`.

The pure matrix lives in `runtime.regime.gate.regime_allows(side, state)`.
It is for entries only. Cartridge and supervised paths still allow exits to
follow their normal rules so positions can flatten when the regime leaves
`TREND_*`.

### Cartridge eval

Cartridge eval accepts an optional Phase 2 hard-veto flag:

```bash
python3.12 -m runtime.tools.eval_run cartridge \
  --id ichi_tk_cloud_strong_v0 \
  --symbol PF_XBTUSD \
  --tf 1h \
  --metrics-only \
  --fee-bps 4 \
  --regime-tf 4h \
  --regime-htf 1d
```

For each 1h decision bar, eval resamples stored 1h OHLCV into the requested
regime timeframe, classifies labels, and maps the decision to the latest label
with `as_of <= bar ts_ms`. The gate blocks only new long/short entries; cartridge
exits and final flatten accounting remain unchanged.

Trend-only cartridges currently require the regime flag and fail closed if it
is omitted:

- `ichi_tk_strong_trend_only_v0`
- `ichi_kijun_bounce_trend_v0`

The kijun-bounce cartridge adds a paper eval entry mode:

- long when prior close was at/below prior kijun, current close crosses above
  kijun, current close is above the displaced kumo top, and close-mode Chikou
  confirms;
- short mirrors below kijun and the displaced kumo bottom.

### Phase 2 ablation drafts

Phase 2 ablations are explicit draft cartridges only; they do not weaken the
default hard-veto spine and do not change supervised paper defaults. The eval
harness recognizes optional `regime.params.phase2_ablation` metadata on these
cartridges and maps it into classifier component switches. When the metadata is
absent, existing cartridge behavior is unchanged.

Run each cartridge on its declared symbol with forced 70/30 fee-on OOS and an
honest trial count covering the whole ablation set:

```bash
python3.12 -m runtime.tools.eval_run cartridge \
  --id <ablation_cartridge_id> \
  --symbol <PF_XBTUSD-or-PF_ETHUSD> \
  --tf 1h \
  --fee-bps 4 \
  --oos-split 0.7 \
  --atr-period 14 \
  --trial-count 12 \
  --metrics-only
```

For every cartridge except AB-0, include the full Phase 2 CLI context:

```bash
  --regime-tf 4h --regime-htf 1d
```

AB-0 is the no-gate baseline. It has `phase2_ablation.enabled=false`, so it can
be run without `--regime-tf`; if the regime flags are accidentally supplied, the
cartridge metadata still disables the Phase 2 eval gate for that draft.

| Ablation | PF_XBTUSD cartridge | PF_ETHUSD cartridge | Component delta |
|---|---|---|---|
| AB-0 | `ichi_p2_ab0_xbt_v0` | `ichi_p2_ab0_eth_v0` | No Phase 2 hard veto. |
| AB-FULL | `ichi_p2_abfull_xbt_v0` | `ichi_p2_abfull_eth_v0` | ADX/DI, kumo width/ATR, 1d HTF veto, dwell/hysteresis all enabled. |
| AB-noADX | `ichi_p2_abnoadx_xbt_v0` | `ichi_p2_abnoadx_eth_v0` | Disable only ADX/+DI/-DI. |
| AB-noWidth | `ichi_p2_abnowidth_xbt_v0` | `ichi_p2_abnowidth_eth_v0` | Disable only kumo width / ATR filtering. |
| AB-noHTF | `ichi_p2_abnohtf_xbt_v0` | `ichi_p2_abnohtf_eth_v0` | Disable only the 1d higher-timeframe veto. |
| AB-noDwell | `ichi_p2_abnodwell_xbt_v0` | `ichi_p2_abnodwell_eth_v0` | Disable only dwell/hysteresis. |

Report ATR-normalized metrics, especially ATR Calmar/MAR and DSR. A component
earns its place only when removing it materially worsens ATR Calmar or DSR on
both PF_XBTUSD and PF_ETHUSD versus AB-FULL. Count every ablation cartridge
toward honest trial N even if a later memo only highlights a subset.

### Supervised paper

The human-triggered supervised runner remains unchanged by default. Operators
can opt into the Phase 2 veto:

```bash
python3.12 -m runtime.tools.supervised_paper \
  --trial-id T-example \
  --side buy \
  --client-order-id aura-example \
  --notional-usd 100 \
  --require-regime
```

With `--require-regime`, the runner reads stored 1h OHLCV under `AURA_ROOT`,
computes the latest regime label, and rejects before any futures-paper venue
call when the side is not allowed. The decision JSONL records
`inputs.regime_gate` and a `risk_gate.reasons[]` entry of `regime_veto`.
