# Aura research cartridge schema

Cartridges are YAML files that describe paper-only Ichimoku research hypotheses.
They are not trading instructions and do not grant runtime authority.

Default venue context:

- `symbol`: `PF_XBTUSD`
- `tf`: `1h`
- `baseline_ref`: `ichimoku_v0`

## Required fields

| Field | Type | Required | Allowed values / notes |
|---|---:|---:|---|
| `id` | string | yes | Stable snake_case id matching the file stem when possible. |
| `title` | string | yes | Human-readable short title. |
| `status` | enum | yes | `draft`, `queued`, `tested`, `killed`, `kept`, `champion_control`, or `scarred_control`. |
| `thesis` | string | yes | One short paragraph describing the hypothesis. |
| `symbol` | string | yes | Default `PF_XBTUSD`; other Kraken futures-paper symbols require CoS review. |
| `tf` | string | yes | Default `1h`; should match stored OHLCV timeframes. Explicit eval experiments may use supported non-default frames such as `4h` only when that stored OHLCV exists. |
| `baseline_ref` | string | yes | Default `ichimoku_v0`. |
| `ichimoku` | object | yes | Contains positive integer `tenkan`, `kijun`, `senkou_b`, and `displacement`. |
| `entry_rules` | object | yes | Structured rule vocabulary; see below. |
| `exit_rules` | object | yes | Structured rule vocabulary; see below. |
| `regime` | object | yes | Optional in behavior, required as an object. Use `type: none` when disabled. |
| `kill_criteria` | object | yes | Numeric gates and baseline comparison flags; see below. |
| `sources` | list[string] | yes | URLs or repo-local docs that motivated the thesis. |
| `notes` | string | no | Extra implementation/backtest notes. |

## Status vocabulary

- `draft`, `queued`, and `tested` track pre-disposition paper research state.
- `killed` records a failed cartridge that must not be revived under the same id.
- `kept` records a provisional paper keep. It does not authorize live trading or
  runner promotion.
- `champion_control` records the best residual paper control after a later
  honesty pass. It is a benchmark/control, not a runner and not live authority.
- `scarred_control` records a paper control with known scars after a later
  honesty pass. It is not a runner, not live authority, and not a forever-kill.

## Ichimoku parameters

```yaml
ichimoku:
  tenkan: 9
  kijun: 26
  senkou_b: 52
  displacement: 26
```

All four values must be positive integers. The current baseline uses
`9/26/52/26`; parameter variants should keep a matching `baseline_ref` so eval
can compare them with the same market data and naive execution assumptions.

## Entry rule vocabulary

Allowed `entry_rules` keys:

| Key | Type | Allowed values / notes |
|---|---:|---|
| `mode` | enum | `always_on`, `tk_cross`, `cloud_bias`, `tk_cloud_bias`, `kijun_bounce`, `tenkan_bounce`, `kumo_break`. |
| `allowed_sides` | list[enum] | Each item is `long` or `short`. |
| `require_close_vs_cloud` | enum | `above_for_long_below_for_short`, `outside_cloud`, `none`. |
| `require_tk_state` | enum | `tenkan_over_kijun_for_long_under_for_short`, `tk_cross_only`, `none`. |
| `require_chikou_confirmation` | bool | Mirrors Ichimoku v0 Chikou confirmation when `true`. |
| `chikou_mode` | enum | `close` compares close vs close[t-displacement]; `strict` compares long close vs high[t-displacement] and short close vs low[t-displacement]. |
| `confirm_symbol` | string | Optional same-bar confirmation symbol, for example `PF_XBTUSD`. Requires `require_confirm_same_bar: true`. |
| `require_confirm_same_bar` | bool | Optional confirm gate. When `true`, entries fail closed unless `confirm_symbol` has a candle with the exact same `ts_ms`, a matching Phase 2 `TREND_*` side under `--regime-tf`/`--regime-htf`, and same-side always-on close-vs-cloud plus TK agreement. |
| `require_kijun_dip_setup` | bool | Optional TK-strong refinement. When `true`, a bullish TK reclaim requires at least one of the prior `setup_bars` to have Tenkan <= Kijun; short mirrors with Tenkan >= Kijun. |
| `require_cloud_color_align` | bool | Optional TK-strong refinement. When `true`, long entries require displaced Span A > Span B and short entries require Span A < Span B. |
| `setup_bars` | integer | Optional positive lookback for setup refinements such as `require_kijun_dip_setup`. |

`kumo_break` is a close-through-cloud breakout mode: long fires when the prior
close was at or below the prior Kumo top and the current close is above the
current Kumo top; short mirrors with the prior close at or above the prior Kumo
bottom and the current close below the current Kumo bottom.

`tenkan_bounce` is a Tenkan reclaim mode: long fires when the prior close was
at or below prior Tenkan, current close is above current Tenkan, and current
close is above the Kumo top; short mirrors below Tenkan and the Kumo bottom.

`confirm_symbol` is intentionally explicit, not inferred from the traded symbol.
Current runnable confirm semantics are same-bar only: the eval harness loads the
confirm symbol's stored OHLCV, computes its own Phase 2 labels under the CLI
`--regime-tf`/`--regime-htf` settings, and denies a non-flat entry unless the
confirm bar at the same timestamp allows the same side and agrees on the
always-on cloud/TK direction. Missing confirm candles, missing labels, timestamp
misalignment, or confirm-side disagreement fail closed. Confirm gates only block
new entries; exits continue to follow `exit_rules`.

Baseline Ichimoku v0 is represented as:

```yaml
entry_rules:
  mode: always_on
  allowed_sides:
    - long
    - short
  require_close_vs_cloud: above_for_long_below_for_short
  require_tk_state: tenkan_over_kijun_for_long_under_for_short
  require_chikou_confirmation: true
  chikou_mode: close
```

The eval harness also supports Chikou-off `always_on` cartridges with the same
cloud-side and TK-state gates, plus `cloud_bias` cartridges with
`require_tk_state: none` and `require_chikou_confirmation: false`. These are
paper-only state filters; Phase 2 thin-spine vetoes still come from explicit CLI
flags such as `--regime-tf 4h --regime-htf 1d`, not from `regime.type`.

## Exit rule vocabulary

Allowed `exit_rules` keys:

| Key | Type | Allowed values / notes |
|---|---:|---|
| `mode` | enum | `bias_flip`, `flat_on_rule_fail`, `opposite_signal`, `time_stop`, `regime_exit`, `kijun_trail`, `atr_stop`, `chandelier_trail`. |
| `close_on_flat` | bool | Exit when the evaluated rule returns flat. |
| `close_on_opposite` | bool | Exit and optionally reverse when the opposite side fires. |
| `max_bars_in_trade` | integer/null | Optional time stop. Use `null` when disabled. |
| `kijun_period` | integer | Optional override for `kijun_trail`; omitted uses `ichimoku.kijun`. |
| `atr_period` | integer | Optional ATR period for `atr_stop` and `chandelier_trail`; default `14`. |
| `atr_mult` | number | Optional ATR multiplier for `atr_stop` and `chandelier_trail`; default `3.0`. |
| `chandelier_period` | integer | Optional high/low lookback for `chandelier_trail`; default `22`. |

Baseline Ichimoku v0 uses `mode: bias_flip`, `close_on_flat: true`, and
`close_on_opposite: true`.

`time_stop` keeps the normal flat/opposite exit behavior and additionally exits
after `max_bars_in_trade` completed bars in the open paper position. It does not
re-enter on the same decision bar that triggered the time stop.

`regime_exit` is only meaningful when Phase 2 regime flags such as
`--regime-tf 4h --regime-htf 1d` are active. Entries still require the normal
TREND side lock; while a position is open, the evaluator flattens a long when
the current label is no longer `TREND_BULL` and flattens a short when the current
label is no longer `TREND_BEAR`.

Track C trail/stop modes are closed-bar paper exits. They do not call venues,
place orders, or imply live stop authority. If an entry would require an
unavailable Kijun/ATR/Chandelier level, eval fails closed by skipping that paper
entry.

- `kijun_trail`: exits a long when the closed-bar close is below
  `Kijun(kijun_period)`, and exits a short when close is above Kijun. Omit
  `kijun_period` to reuse `ichimoku.kijun`.
- `atr_stop`: initializes a static stop from the entry decision bar ATR:
  long stop = entry price - `atr_mult * ATR(atr_period)`, short stop = entry
  price + `atr_mult * ATR(atr_period)`. The closed-bar close crossing that level
  triggers a paper exit at the existing next-open execution assumption.
- `chandelier_trail`: initializes and tightens a Chandelier line using only bars
  available through the evaluated close. Long raw trail =
  `highest_high(chandelier_period) - atr_mult * ATR(atr_period)`; short raw trail
  = `lowest_low(chandelier_period) + atr_mult * ATR(atr_period)`. The stored
  trail is tighten-only: non-decreasing for longs and non-increasing for shorts.

## Regime gates

`regime` is required as an object so loaders can always inspect it, but the
disabled form is explicit:

```yaml
regime:
  type: none
  params: {}
```

Draft Phase 2 ablation cartridges may carry explicit eval-only component
metadata under `regime.params.phase2_ablation` while keeping
`regime.type: none` for the local cartridge gate:

```yaml
regime:
  type: none
  params:
    phase2_ablation:
      enabled: true
      label: AB-noADX
      components:
        adx_di: false
        kumo_width_atr: true
        htf_veto: true
        dwell_hysteresis: true
```

`enabled: false` is the explicit no-Phase-2-veto ablation path. When omitted,
existing cartridges keep the current default behavior: no local cartridge regime
gate, and the Phase 2 CLI hard veto applies only when requested or required by a
known trend cartridge id.

Allowed `regime.type` values:

- `none`: no regime filter.
- `adx`: only admit signals when Average Directional Index is above a threshold.
  Proposed first defaults are `period: 14`, `threshold: 20` or `25`.
- `er`: Kaufman Efficiency Ratio chop filter. Current runnable params:
  `period`, `threshold`; entries are admitted when ER is at or above the
  threshold.
- `cloud_thickness`: only trade when Ichimoku cloud thickness exceeds a minimum.
  Current runnable params: `min_pct`, computed as
  `(kumo_top - kumo_bot) / close * 100` from displaced spans.

Runnable regime gates fail closed: if the gate cannot be computed, no new entry
is admitted. Exits continue to follow the cartridge exit rules.

## Kill criteria vocabulary

Allowed `kill_criteria` keys:

| Key | Type | Notes |
|---|---:|---|
| `max_dd_points` | number | Kill if max drawdown exceeds this many points. |
| `min_trades` | integer | Kill or retest if sample size is below this threshold. |
| `must_beat_baseline` | bool | If true, compare against `baseline_ref`. |
| `baseline_metric` | enum | `total_pnl_points`, `total_pnl_points_after_fees`, `max_drawdown_points`, `win_rate`, `profit_factor`, `atr_normalized_total_return`. |
| `notes` | string | Plain-language CoS kill/keep instruction. |

## Tiny validation example

Use the runtime stub to load and validate all seed cartridges without adding
runtime trading behavior:

```bash
python - <<'PY'
from pathlib import Path
from runtime.research.cartridge import load_cartridge

for path in sorted(Path("research/cartridges").glob("*.yaml")):
    cartridge = load_cartridge(path)
    print(cartridge["id"], cartridge["status"], cartridge["baseline_ref"])
PY
```

The loader intentionally supports only the small YAML subset used by these
cartridges. Keep documents boring: mappings, scalar values, and scalar lists.
