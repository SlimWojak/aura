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
| `status` | enum | yes | `draft`, `queued`, `tested`, `killed`, or `kept`. |
| `thesis` | string | yes | One short paragraph describing the hypothesis. |
| `symbol` | string | yes | Default `PF_XBTUSD`; other Kraken futures-paper symbols require CoS review. |
| `tf` | string | yes | Default `1h`; should match stored OHLCV timeframes. |
| `baseline_ref` | string | yes | Default `ichimoku_v0`. |
| `ichimoku` | object | yes | Contains positive integer `tenkan`, `kijun`, `senkou_b`, and `displacement`. |
| `entry_rules` | object | yes | Structured rule vocabulary; see below. |
| `exit_rules` | object | yes | Structured rule vocabulary; see below. |
| `regime` | object | yes | Optional in behavior, required as an object. Use `type: none` when disabled. |
| `kill_criteria` | object | yes | Numeric gates and baseline comparison flags; see below. |
| `sources` | list[string] | yes | URLs or repo-local docs that motivated the thesis. |
| `notes` | string | no | Extra implementation/backtest notes. |

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

## Exit rule vocabulary

Allowed `exit_rules` keys:

| Key | Type | Allowed values / notes |
|---|---:|---|
| `mode` | enum | `bias_flip`, `flat_on_rule_fail`, `opposite_signal`, `time_stop`. |
| `close_on_flat` | bool | Exit when the evaluated rule returns flat. |
| `close_on_opposite` | bool | Exit and optionally reverse when the opposite side fires. |
| `max_bars_in_trade` | integer/null | Optional time stop. Use `null` when disabled. |

Baseline Ichimoku v0 uses `mode: bias_flip`, `close_on_flat: true`, and
`close_on_opposite: true`.

## Regime gates

`regime` is required as an object so loaders can always inspect it, but the
disabled form is explicit:

```yaml
regime:
  type: none
  params: {}
```

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
| `baseline_metric` | enum | `total_pnl_points`, `total_pnl_points_after_fees`, `max_drawdown_points`, `win_rate`, `profit_factor`. |
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
