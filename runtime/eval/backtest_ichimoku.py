"""Paper-only backtest harness for Ichimoku v0 bias.

This module is intentionally thin: it reuses ``runtime.brain.ichimoku`` for
indicator math and never calls Kraken, systemd, or any constellation path.

Lookahead note
--------------
The fast path computes one full Ichimoku series and then indexes the signal for
each evaluated candle. This preserves the no-lookahead rule because the brain's
displaced cloud values at bar ``t`` come from raw Tenkan/Kijun/Senkou values
calculated 26 bars in the past, and the Chikou rule compares the current close
to ``close[t-26]``. The only future price used is the deliberately naive
execution assumption: decisions at bar ``t`` execute at bar ``t+1`` open when
available, otherwise at bar ``t`` close.
"""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
import json
from typing import Any, Callable, Mapping, Sequence

from runtime.brain import compute_ichimoku, signal_from_series
from runtime.brain.types import Bias, IchimokuParams, IchimokuSignal
from runtime.market import ohlcv_path, read_candles, validate_symbol, validate_tf
from runtime.research.cartridge import load_cartridge, load_cartridges


BACKTEST_REPORT_SCHEMA = "aura.backtest_report.v1"
BACKTEST_TRADE_SCHEMA = "aura.backtest_trade.v1"
FEE_ASSUMPTION = 0
MODEL_DESCRIPTION = (
    "naive_v0: one position at a time, one unit notional in price points, "
    "next-bar-open execution when available else current close, no leverage, "
    "no fees, no slippage"
)
FAST_ENGINE = "precomputed_ichimoku_series_v1"
CARTRIDGE_ENGINE = "precomputed_ichimoku_cartridge_v1"
REFERENCE_ENGINE = "reference_slice_recompute_v1"
CARTRIDGE_ROOT = Path(__file__).resolve().parents[2] / "research" / "cartridges"

_DIRECTION_BY_BIAS: dict[Bias, int] = {"long": 1, "short": -1, "flat": 0}
_BIAS_BY_DIRECTION = {1: "long", -1: "short"}
_ALLOW_ENTRY_GATE = {"allowed": True, "reason": "no_entry_gate", "values": {}}
_SignalProvider = Callable[[int], IchimokuSignal]
_EntryGateProvider = Callable[[int], Mapping[str, Any]]


def run_backtest(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    tf: str,
    params: IchimokuParams | None = None,
    min_bars: int | None = None,
) -> dict[str, Any]:
    """Walk historical candles and score the v0 Ichimoku bias.

    The position model is intentionally dumb and documented in the output:

    - flat -> long/short enters at the next bar open when available;
    - long/short -> flat exits at the next bar open when available;
    - long -> short, or short -> long, exits then enters the opposite side at
      the same execution price;
    - a remaining position is closed at the final candle close for accounting;
    - size is one price-point unit with no leverage, fees, or slippage.
    """

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    resolved_params = params if params is not None else IchimokuParams()
    resolved_min_bars = min_bars if min_bars is not None else resolved_params.minimum_candles
    normalized = _prepare_candles(
        candles,
        min_bars=resolved_min_bars,
        symbol=safe_symbol,
        tf=safe_tf,
        params=resolved_params,
    )
    if isinstance(normalized, dict):
        return normalized

    series = compute_ichimoku(normalized, params=resolved_params)
    return _score_backtest(
        normalized,
        symbol=safe_symbol,
        tf=safe_tf,
        params=resolved_params,
        min_bars=resolved_min_bars,
        engine=FAST_ENGINE,
        lookahead_note=(
            "Signals are indexed from one precomputed Ichimoku series. "
            "Displaced spans use past raw Ichimoku values, and Chikou compares "
            "current close to close[t-26] per runtime.brain.ichimoku. Execution "
            "uses next open when available, else current close."
        ),
        signal_provider=lambda index: signal_from_series(series, index=index),
    )


def run_backtest_cartridge(
    candles: Sequence[Mapping[str, Any]],
    *,
    cartridge: Mapping[str, Any],
    symbol: str | None = None,
    tf: str | None = None,
    min_bars: int | None = None,
) -> dict[str, Any]:
    """Run a supported paper research cartridge over supplied candles."""

    unsupported = unsupported_cartridge_reasons(cartridge)
    if unsupported:
        raise NotImplementedError(
            f"cartridge {cartridge.get('id', '<unknown>')} is not runnable: "
            + "; ".join(unsupported)
        )

    safe_symbol = validate_symbol(symbol if symbol is not None else str(cartridge["symbol"]))
    safe_tf = validate_tf(tf if tf is not None else str(cartridge["tf"]))
    params = _params_from_cartridge(cartridge)
    resolved_min_bars = min_bars if min_bars is not None else params.minimum_candles
    normalized = _prepare_candles(
        candles,
        min_bars=resolved_min_bars,
        symbol=safe_symbol,
        tf=safe_tf,
        params=params,
    )
    if isinstance(normalized, dict):
        _attach_cartridge_metadata(normalized, cartridge=cartridge, runnable=True)
        return normalized

    entry_rules = _mapping(cartridge, "entry_rules")
    chikou_mode = str(entry_rules["chikou_mode"])
    allowed_sides = set(entry_rules["allowed_sides"])
    allowed_entry_sides = None if allowed_sides == {"long", "short"} else allowed_sides
    series = compute_ichimoku(normalized, params=params)
    entry_gate_provider = _entry_gate_provider(normalized, cartridge=cartridge)
    report = _score_backtest(
        normalized,
        symbol=safe_symbol,
        tf=safe_tf,
        params=params,
        min_bars=resolved_min_bars,
        engine=CARTRIDGE_ENGINE,
        lookahead_note=(
            "Signals are indexed from one precomputed Ichimoku series. "
            "Displaced spans use past raw Ichimoku values. Chikou mode is "
            f"{chikou_mode!r}; strict mode compares current close with "
            "high/low[t-displacement]. Entry regime gates are precomputed once "
            "and only block new entries. Execution uses next open when available, "
            "else current close."
        ),
        signal_provider=lambda index: signal_from_series(
            series,
            index=index,
            chikou_mode=chikou_mode,  # type: ignore[arg-type]
        ),
        entry_gate_provider=entry_gate_provider,
        allowed_entry_sides=allowed_entry_sides,
    )
    _attach_cartridge_metadata(report, cartridge=cartridge, runnable=True)
    return report


def run_backtest_reference(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    tf: str,
    params: IchimokuParams | None = None,
    min_bars: int | None = None,
) -> dict[str, Any]:
    """Reference implementation that recomputes Ichimoku from each prefix.

    This intentionally keeps the old O(n^2)-shaped signal path available for
    tests that prove the precomputed fast path produces matching decisions.
    """

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    resolved_params = params if params is not None else IchimokuParams()
    resolved_min_bars = min_bars if min_bars is not None else resolved_params.minimum_candles
    normalized = _prepare_candles(
        candles,
        min_bars=resolved_min_bars,
        symbol=safe_symbol,
        tf=safe_tf,
        params=resolved_params,
    )
    if isinstance(normalized, dict):
        return normalized

    return _score_backtest(
        normalized,
        symbol=safe_symbol,
        tf=safe_tf,
        params=resolved_params,
        min_bars=resolved_min_bars,
        engine=REFERENCE_ENGINE,
        lookahead_note=(
            "Signals are recomputed from candles[:index+1]. Displaced spans use "
            "past raw Ichimoku values, and Chikou compares current close to "
            "close[t-26] per runtime.brain.ichimoku. Execution uses next open "
            "when available, else current close."
        ),
        signal_provider=lambda index: signal_for_closed_bar(
            normalized,
            index=index,
            params=resolved_params,
        ),
    )


def _prepare_candles(
    candles: Sequence[Mapping[str, Any]],
    *,
    min_bars: int,
    symbol: str,
    tf: str,
    params: IchimokuParams,
) -> list[dict[str, float | int | None]] | dict[str, Any]:
    if min_bars <= 0:
        raise ValueError("min_bars must be positive")

    normalized = [_normalize_candle(index, candle) for index, candle in enumerate(candles)]
    if len(normalized) < min_bars:
        return _insufficient_history_report(
            symbol=symbol,
            tf=tf,
            candle_count=len(normalized),
            min_bars=min_bars,
            params=params,
        )
    return normalized


def _score_backtest(
    candles: Sequence[Mapping[str, float | int | None]],
    *,
    symbol: str,
    tf: str,
    params: IchimokuParams,
    min_bars: int,
    engine: str,
    lookahead_note: str,
    signal_provider: _SignalProvider,
    entry_gate_provider: _EntryGateProvider | None = None,
    allowed_entry_sides: set[str] | None = None,
) -> dict[str, Any]:
    if min_bars <= 0:
        raise ValueError("min_bars must be positive")

    start_index = min_bars - 1
    bias_counts: dict[str, int] = {"long": 0, "short": 0, "flat": 0}
    signal_trace: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    equity_points = 0.0
    peak_equity_points = 0.0
    max_drawdown_points = 0.0
    bars_in_market = 0
    final_bias: Bias = "flat"
    position: dict[str, Any] | None = None

    for index in range(start_index, len(candles)):
        signal = signal_provider(index)
        entry_gate = (
            _normalize_entry_gate(entry_gate_provider(index))
            if entry_gate_provider is not None
            else _ALLOW_ENTRY_GATE
        )
        if (
            allowed_entry_sides is not None
            and signal.bias != "flat"
            and signal.bias not in allowed_entry_sides
        ):
            entry_gate = {
                "allowed": False,
                "reason": "side_not_allowed",
                "values": {"bias": signal.bias},
            }
        final_bias = signal.bias
        bias_counts[signal.bias] += 1
        desired_direction = _DIRECTION_BY_BIAS[signal.bias]
        execution = _execution(candles, index)
        signal_trace.append(
            {
                "index": index,
                "ts_ms": candles[index]["ts_ms"],
                "ok": signal.ok,
                "reason": signal.reason,
                "bias": signal.bias,
                "execution_index": execution["index"],
                "execution_price": _stable_float(execution["price"]),
                "execution_basis": execution["basis"],
            }
        )
        if entry_gate_provider is not None or allowed_entry_sides is not None:
            signal_trace[-1]["entry_gate"] = entry_gate

        current_direction = int(position["direction"]) if position is not None else 0
        if current_direction != 0 and desired_direction != current_direction:
            trade = _close_trade(
                position=position,
                exit_execution=execution,
                exit_reason=f"bias_{signal.bias}",
            )
            trades.append(trade)
            equity_points += float(trade["pnl_points"])
            peak_equity_points = max(peak_equity_points, equity_points)
            max_drawdown_points = max(max_drawdown_points, peak_equity_points - equity_points)
            position = None

        if desired_direction != 0 and position is None and bool(entry_gate["allowed"]):
            position = _open_position(
                direction=desired_direction,
                entry_execution=execution,
                entry_reason=f"bias_{signal.bias}",
            )

        if position is not None:
            bars_in_market += 1
            if int(position["entry_index"]) <= index:
                marked_equity_points = equity_points + _unrealized_pnl(
                    position=position,
                    mark_price=float(candles[index]["close"]),
                )
                peak_equity_points = max(peak_equity_points, marked_equity_points)
                max_drawdown_points = max(
                    max_drawdown_points,
                    peak_equity_points - marked_equity_points,
                )

    if position is not None and candles:
        final_execution = {
            "index": len(candles) - 1,
            "ts_ms": candles[-1]["ts_ms"],
            "price": candles[-1]["close"],
            "basis": "final_close",
        }
        trade = _close_trade(
            position=position,
            exit_execution=final_execution,
            exit_reason="end_of_data",
        )
        trades.append(trade)
        equity_points += float(trade["pnl_points"])
        peak_equity_points = max(peak_equity_points, equity_points)
        max_drawdown_points = max(max_drawdown_points, peak_equity_points - equity_points)

    trade_count = len(trades)
    winning_trades = sum(1 for trade in trades if float(trade["pnl_points"]) > 0)
    evaluated_bars = len(signal_trace)
    total_pnl_points = sum(float(trade["pnl_points"]) for trade in trades)
    report = {
        "schema": BACKTEST_REPORT_SCHEMA,
        "ok": True,
        "generated_at": utc_now_iso(),
        "symbol": symbol,
        "tf": tf,
        "candle_count": len(candles),
        "evaluated_bars": evaluated_bars,
        "min_bars": min_bars,
        "params": params.to_dict(),
        "fee_assumption": FEE_ASSUMPTION,
        "naive": True,
        "model": MODEL_DESCRIPTION,
        "engine": engine,
        "lookahead_note": lookahead_note,
        "metrics": {
            "trade_count": trade_count,
            "win_rate": (winning_trades / trade_count) if trade_count else 0.0,
            "total_pnl_points": _stable_float(total_pnl_points),
            "max_drawdown_points": _stable_float(max_drawdown_points),
            "time_in_market": (bars_in_market / evaluated_bars) if evaluated_bars else 0.0,
            "bars_in_market": bars_in_market,
            "bias_counts": bias_counts,
            "final_bias": final_bias,
        },
        "trades": trades,
        "signals": signal_trace,
    }
    return report


def backtest_from_store(
    *,
    symbol: str,
    tf: str,
    aura_root: str | Path | None = None,
    min_bars: int | None = None,
    max_bars: int | None = None,
    since_ts_ms: int | None = None,
) -> dict[str, Any]:
    """Read stored OHLCV and return a backtest report."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    candles = read_candles(safe_symbol, safe_tf, aura_root_override=aura_root)
    windowed_candles = _window_candles(candles, max_bars=max_bars, since_ts_ms=since_ts_ms)
    report = run_backtest(windowed_candles, symbol=safe_symbol, tf=safe_tf, min_bars=min_bars)
    report["market_path"] = str(ohlcv_path(safe_symbol, safe_tf, aura_root_override=aura_root))
    report["source_candle_count"] = len(candles)
    report["window"] = {
        "since_ts_ms": since_ts_ms,
        "max_bars": max_bars,
        "first_ts_ms": _candle_ts_ms(windowed_candles[0]) if windowed_candles else None,
        "last_ts_ms": _candle_ts_ms(windowed_candles[-1]) if windowed_candles else None,
    }
    return report


def cartridge_backtest_from_store(
    *,
    cartridge_id: str | None = None,
    cartridge_path: str | Path | None = None,
    symbol: str | None = None,
    tf: str | None = None,
    aura_root: str | Path | None = None,
    min_bars: int | None = None,
    max_bars: int | None = None,
    since_ts_ms: int | None = None,
    cartridge_root: str | Path = CARTRIDGE_ROOT,
) -> dict[str, Any]:
    """Read stored OHLCV and return a supported cartridge backtest report."""

    cartridge = resolve_cartridge(
        cartridge_id=cartridge_id,
        cartridge_path=cartridge_path,
        cartridge_root=cartridge_root,
    )
    unsupported = unsupported_cartridge_reasons(cartridge)
    if unsupported:
        raise NotImplementedError(
            f"cartridge {cartridge.get('id', '<unknown>')} is not runnable: "
            + "; ".join(unsupported)
        )
    safe_symbol = validate_symbol(symbol if symbol is not None else str(cartridge["symbol"]))
    safe_tf = validate_tf(tf if tf is not None else str(cartridge["tf"]))
    candles = read_candles(safe_symbol, safe_tf, aura_root_override=aura_root)
    windowed_candles = _window_candles(candles, max_bars=max_bars, since_ts_ms=since_ts_ms)
    report = run_backtest_cartridge(
        windowed_candles,
        cartridge=cartridge,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
    )
    report["market_path"] = str(ohlcv_path(safe_symbol, safe_tf, aura_root_override=aura_root))
    report["source_candle_count"] = len(candles)
    report["window"] = {
        "since_ts_ms": since_ts_ms,
        "max_bars": max_bars,
        "first_ts_ms": _candle_ts_ms(windowed_candles[0]) if windowed_candles else None,
        "last_ts_ms": _candle_ts_ms(windowed_candles[-1]) if windowed_candles else None,
    }
    return report


def resolve_cartridge(
    *,
    cartridge_id: str | None = None,
    cartridge_path: str | Path | None = None,
    cartridge_root: str | Path = CARTRIDGE_ROOT,
) -> dict[str, Any]:
    """Load one cartridge by id or explicit path."""

    if bool(cartridge_id) == bool(cartridge_path):
        raise ValueError("provide exactly one of cartridge_id or cartridge_path")
    if cartridge_path is not None:
        return load_cartridge(cartridge_path)
    assert cartridge_id is not None
    if "/" in cartridge_id or "\\" in cartridge_id or cartridge_id.endswith(".yaml"):
        raise ValueError("cartridge id must be an id, not a path")
    path = Path(cartridge_root) / f"{cartridge_id}.yaml"
    if not path.exists():
        raise ValueError(f"unknown cartridge id: {cartridge_id}")
    return load_cartridge(path)


def runnable_cartridge_ids(cartridge_root: str | Path = CARTRIDGE_ROOT) -> list[str]:
    """Return currently runnable cartridge ids in stable order."""

    return [
        str(cartridge["id"])
        for cartridge in load_cartridges(cartridge_root)
        if not unsupported_cartridge_reasons(cartridge)
    ]


def unsupported_cartridge_reasons(cartridge: Mapping[str, Any]) -> list[str]:
    """Explain why a cartridge cannot yet run in the minimal eval harness."""

    reasons: list[str] = []
    entry_rules = _mapping(cartridge, "entry_rules")
    exit_rules = _mapping(cartridge, "exit_rules")
    regime = _mapping(cartridge, "regime")

    if entry_rules["mode"] != "always_on":
        reasons.append(f"entry_rules.mode={entry_rules['mode']!r} is not wired")
    if entry_rules["require_close_vs_cloud"] != "above_for_long_below_for_short":
        reasons.append(
            "entry_rules.require_close_vs_cloud="
            f"{entry_rules['require_close_vs_cloud']!r} is not wired"
        )
    if entry_rules["require_tk_state"] != "tenkan_over_kijun_for_long_under_for_short":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if not bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=false is not wired")
    if entry_rules["chikou_mode"] not in {"close", "strict"}:
        reasons.append(f"entry_rules.chikou_mode={entry_rules['chikou_mode']!r} is not wired")
    if exit_rules["mode"] != "bias_flip":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if not bool(exit_rules["close_on_flat"]):
        reasons.append("exit_rules.close_on_flat=false is not wired")
    if not bool(exit_rules["close_on_opposite"]):
        reasons.append("exit_rules.close_on_opposite=false is not wired")
    if exit_rules["max_bars_in_trade"] is not None:
        reasons.append("exit_rules.max_bars_in_trade is not wired")
    if regime["type"] not in {"none", "adx"}:
        reasons.append(f"regime.type={regime['type']!r} is not wired")

    return reasons


def compute_wilder_adx(
    candles: Sequence[Mapping[str, Any]],
    *,
    period: int,
) -> list[float | None]:
    """Compute Wilder ADX values aligned to the input candles."""

    if period <= 0:
        raise ValueError("ADX period must be positive")

    highs = [
        _finite_float(candle.get("high"), field_name=f"candles[{index}].high")
        for index, candle in enumerate(candles)
    ]
    lows = [
        _finite_float(candle.get("low"), field_name=f"candles[{index}].low")
        for index, candle in enumerate(candles)
    ]
    closes = [
        _finite_float(candle.get("close"), field_name=f"candles[{index}].close")
        for index, candle in enumerate(candles)
    ]
    count = len(candles)
    adx: list[float | None] = [None] * count
    if count <= period:
        return adx

    true_ranges = [0.0] * count
    plus_dm = [0.0] * count
    minus_dm = [0.0] * count
    for index in range(1, count):
        high = highs[index]
        low = lows[index]
        previous_high = highs[index - 1]
        previous_low = lows[index - 1]
        previous_close = closes[index - 1]
        true_ranges[index] = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )
        up_move = high - previous_high
        down_move = previous_low - low
        plus_dm[index] = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm[index] = down_move if down_move > up_move and down_move > 0 else 0.0

    dx: list[float | None] = [None] * count
    smoothed_tr = sum(true_ranges[1 : period + 1])
    smoothed_plus_dm = sum(plus_dm[1 : period + 1])
    smoothed_minus_dm = sum(minus_dm[1 : period + 1])
    dx[period] = _dx(smoothed_tr, smoothed_plus_dm, smoothed_minus_dm)
    for index in range(period + 1, count):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + true_ranges[index]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm[index]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm[index]
        dx[index] = _dx(smoothed_tr, smoothed_plus_dm, smoothed_minus_dm)

    first_adx_index = (2 * period) - 1
    if first_adx_index >= count:
        return adx
    first_dx_values = [value for value in dx[period : first_adx_index + 1] if value is not None]
    if len(first_dx_values) != period:
        return adx
    previous_adx = sum(first_dx_values) / period
    adx[first_adx_index] = previous_adx
    for index in range(first_adx_index + 1, count):
        dx_value = dx[index]
        if dx_value is None:
            continue
        previous_adx = ((previous_adx * (period - 1)) + dx_value) / period
        adx[index] = previous_adx
    return adx


def _params_from_cartridge(cartridge: Mapping[str, Any]) -> IchimokuParams:
    values = _mapping(cartridge, "ichimoku")
    return IchimokuParams(
        tenkan=int(values["tenkan"]),
        kijun=int(values["kijun"]),
        senkou_b=int(values["senkou_b"]),
        displacement=int(values["displacement"]),
    )


def _entry_gate_provider(
    candles: Sequence[Mapping[str, float | int | None]],
    *,
    cartridge: Mapping[str, Any],
) -> _EntryGateProvider | None:
    regime = _mapping(cartridge, "regime")
    regime_type = str(regime["type"])

    if regime_type == "none":
        return None
    elif regime_type == "adx":
        params = _mapping(regime, "params")
        period = _positive_int(params.get("period"), "regime.params.period")
        threshold = _positive_float(params.get("threshold"), "regime.params.threshold")
        adx_values = compute_wilder_adx(candles, period=period)
    else:
        raise NotImplementedError(f"regime.type={regime_type!r} is not wired")

    def gate(index: int) -> Mapping[str, Any]:
        adx_value = adx_values[index]
        values = {"adx": _stable_float(adx_value), "period": period, "threshold": threshold}
        if adx_value is None:
            return {"allowed": False, "reason": "adx_unavailable", "values": values}
        if adx_value < float(threshold):
            return {"allowed": False, "reason": "adx_below_threshold", "values": values}
        return {"allowed": True, "reason": "adx_threshold_met", "values": values}

    return gate


def _normalize_entry_gate(raw_gate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "allowed": bool(raw_gate.get("allowed", False)),
        "reason": str(raw_gate.get("reason", "entry_gate_unspecified")),
        "values": _stable_mapping_values(_mapping_or_empty(raw_gate.get("values"))),
    }


def _attach_cartridge_metadata(
    report: dict[str, Any],
    *,
    cartridge: Mapping[str, Any],
    runnable: bool,
) -> None:
    report["cartridge"] = {
        "id": cartridge["id"],
        "title": cartridge["title"],
        "status": cartridge["status"],
        "baseline_ref": cartridge["baseline_ref"],
        "symbol": cartridge["symbol"],
        "tf": cartridge["tf"],
        "runnable": runnable,
        "ichimoku": dict(_mapping(cartridge, "ichimoku")),
        "entry_rules": dict(_mapping(cartridge, "entry_rules")),
        "exit_rules": dict(_mapping(cartridge, "exit_rules")),
        "regime": dict(_mapping(cartridge, "regime")),
        "kill_criteria": dict(_mapping(cartridge, "kill_criteria")),
    }


def _dx(smoothed_tr: float, smoothed_plus_dm: float, smoothed_minus_dm: float) -> float:
    if smoothed_tr <= 0:
        return 0.0
    plus_di = 100 * (smoothed_plus_dm / smoothed_tr)
    minus_di = 100 * (smoothed_minus_dm / smoothed_tr)
    denominator = plus_di + minus_di
    if denominator <= 0:
        return 0.0
    return 100 * (abs(plus_di - minus_di) / denominator)


def _mapping(values: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = values[field]
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("entry gate values must be a mapping")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _positive_float(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return float(value)


def _stable_mapping_values(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: _stable_float(value) if isinstance(value, float) else value
        for key, value in values.items()
    }


def _window_candles(
    candles: Sequence[Mapping[str, Any]],
    *,
    max_bars: int | None,
    since_ts_ms: int | None,
) -> list[Mapping[str, Any]]:
    if max_bars is not None and max_bars <= 0:
        raise ValueError("max_bars must be positive")
    if since_ts_ms is not None and since_ts_ms <= 0:
        raise ValueError("since_ts_ms must be a positive unix millisecond timestamp")

    filtered = list(candles)
    if since_ts_ms is not None:
        filtered = [candle for candle in filtered if _candle_ts_ms(candle) >= since_ts_ms]
    if max_bars is not None:
        filtered = filtered[-max_bars:]
    return filtered


def signal_for_closed_bar(
    candles: Sequence[Mapping[str, Any]],
    *,
    index: int,
    params: IchimokuParams | None = None,
) -> IchimokuSignal:
    """Compute the signal at ``index`` using no candles after ``index``."""

    if index < 0:
        raise ValueError("index must be non-negative")
    if index >= len(candles):
        raise ValueError("index out of range")
    resolved_params = params if params is not None else IchimokuParams()
    series = compute_ichimoku(candles[: index + 1], params=resolved_params)
    return signal_from_series(series)


def _insufficient_history_report(
    *,
    symbol: str,
    tf: str,
    candle_count: int,
    min_bars: int,
    params: IchimokuParams,
) -> dict[str, Any]:
    return {
        "schema": BACKTEST_REPORT_SCHEMA,
        "ok": False,
        "reason": f"insufficient_history: need at least {min_bars} candles, got {candle_count}",
        "generated_at": utc_now_iso(),
        "symbol": symbol,
        "tf": tf,
        "candle_count": candle_count,
        "evaluated_bars": 0,
        "min_bars": min_bars,
        "params": params.to_dict(),
        "fee_assumption": FEE_ASSUMPTION,
        "naive": True,
        "model": MODEL_DESCRIPTION,
        "metrics": {
            "trade_count": 0,
            "win_rate": 0.0,
            "total_pnl_points": 0.0,
            "max_drawdown_points": 0.0,
            "time_in_market": 0.0,
            "bars_in_market": 0,
            "bias_counts": {"long": 0, "short": 0, "flat": 0},
            "final_bias": "flat",
        },
        "trades": [],
        "signals": [],
    }


def write_report(report: Mapping[str, Any], output_dir: Path) -> dict[str, str]:
    """Write report JSON and JSONL trades into an eval evidence directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    trades_path = output_dir / "trades.jsonl"
    report_path.write_text(
        json.dumps(dict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with trades_path.open("w", encoding="utf-8") as handle:
        for trade in report.get("trades", []):
            handle.write(json.dumps(trade, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    return {"report_json": str(report_path), "trades_jsonl": str(trades_path)}


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _normalize_candle(index: int, candle: Mapping[str, Any]) -> dict[str, float | int | None]:
    return {
        "index": index,
        "ts_ms": _optional_int(candle.get("ts_ms")),
        "open": _finite_float(candle.get("open"), field_name=f"candles[{index}].open"),
        "high": _finite_float(candle.get("high"), field_name=f"candles[{index}].high"),
        "low": _finite_float(candle.get("low"), field_name=f"candles[{index}].low"),
        "close": _finite_float(candle.get("close"), field_name=f"candles[{index}].close"),
    }


def _execution(candles: Sequence[Mapping[str, float | int | None]], index: int) -> dict[str, Any]:
    if index + 1 < len(candles):
        next_candle = candles[index + 1]
        return {
            "index": index + 1,
            "ts_ms": next_candle["ts_ms"],
            "price": next_candle["open"],
            "basis": "next_open",
        }
    current = candles[index]
    return {
        "index": index,
        "ts_ms": current["ts_ms"],
        "price": current["close"],
        "basis": "current_close",
    }


def _open_position(
    *,
    direction: int,
    entry_execution: Mapping[str, Any],
    entry_reason: str,
) -> dict[str, Any]:
    return {
        "direction": direction,
        "entry_index": entry_execution["index"],
        "entry_ts_ms": entry_execution["ts_ms"],
        "entry_price": float(entry_execution["price"]),
        "entry_basis": entry_execution["basis"],
        "entry_reason": entry_reason,
    }


def _close_trade(
    *,
    position: Mapping[str, Any],
    exit_execution: Mapping[str, Any],
    exit_reason: str,
) -> dict[str, Any]:
    direction = int(position["direction"])
    entry_price = float(position["entry_price"])
    exit_price = float(exit_execution["price"])
    pnl_points = (exit_price - entry_price) * direction
    return {
        "schema": BACKTEST_TRADE_SCHEMA,
        "direction": _BIAS_BY_DIRECTION[direction],
        "entry_index": position["entry_index"],
        "entry_ts_ms": position["entry_ts_ms"],
        "entry_price": _stable_float(entry_price),
        "entry_basis": position["entry_basis"],
        "entry_reason": position["entry_reason"],
        "exit_index": exit_execution["index"],
        "exit_ts_ms": exit_execution["ts_ms"],
        "exit_price": _stable_float(exit_price),
        "exit_basis": exit_execution["basis"],
        "exit_reason": exit_reason,
        "pnl_points": _stable_float(pnl_points),
    }


def _unrealized_pnl(*, position: Mapping[str, Any], mark_price: float) -> float:
    direction = int(position["direction"])
    entry_price = float(position["entry_price"])
    return (mark_price - entry_price) * direction


def _finite_float(raw_value: Any, *, field_name: str) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _optional_int(raw_value: Any) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("candle ts_ms must be an integer when present") from exc


def _candle_ts_ms(candle: Mapping[str, Any]) -> int:
    raw_value = candle.get("ts_ms")
    if raw_value in (None, ""):
        raise ValueError("candle ts_ms is required for backtest windowing")
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("candle ts_ms must be an integer") from exc


def _stable_float(value: float) -> float:
    return round(float(value), 10)
