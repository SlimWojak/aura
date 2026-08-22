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

from bisect import bisect_right
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
import json
from typing import Any, Callable, Mapping, Sequence

from runtime.brain import compute_ichimoku, signal_from_series
from runtime.brain.types import Bias, IchimokuParams, IchimokuSignal
from runtime.market import ohlcv_path, read_candles, validate_symbol, validate_tf
from runtime.regime import RegimeParams, classify_series, regime_allows, resample_1h_candles
from runtime.research.cartridge import load_cartridge, load_cartridges


BACKTEST_REPORT_SCHEMA = "aura.backtest_report.v1"
BACKTEST_TRADE_SCHEMA = "aura.backtest_trade.v1"
FEE_ASSUMPTION = "fee_bps defaults to 0; when set, each closed trade deducts entry and exit fees"
FEE_MODEL = "1-unit price-point fees: fee_bps / 10000 * (entry_price + exit_price)"
MODEL_DESCRIPTION = (
    "naive_v0: one position at a time, one unit notional in price points, "
    "next-bar-open execution when available else current close, no leverage, "
    "optional fee_bps accounting, no slippage"
)
FAST_ENGINE = "precomputed_ichimoku_series_v1"
CARTRIDGE_ENGINE = "precomputed_ichimoku_cartridge_v1"
REFERENCE_ENGINE = "reference_slice_recompute_v1"
CARTRIDGE_ROOT = Path(__file__).resolve().parents[2] / "research" / "cartridges"

_DIRECTION_BY_BIAS: dict[Bias, int] = {"long": 1, "short": -1, "flat": 0}
_BIAS_BY_DIRECTION = {1: "long", -1: "short"}
_ALLOW_ENTRY_GATE = {"allowed": True, "reason": "no_entry_gate", "values": {}}
_PHASE2_REGIME_REQUIRED_CARTRIDGES = {
    "ichi_params_20_60_trend_v0",
    "ichi_tk_cross_trend_v0",
    "ichi_kumo_break_trend_v0",
    "ichi_tk_strong_trend_only_v0",
    "ichi_tk_strong_trend_oos_v0",
    "ichi_tk_strong_trend_kijun_dip_v0",
    "ichi_tk_strong_trend_cloud_color_v0",
    "ichi_kijun_bounce_trend_v0",
    "ichi_params_20_60_trend_eth_dd_v0",
    "ichi_params_10_30_trend_v0",
    "ichi_tenkan_bounce_trend_v0",
}
_SignalProvider = Callable[[int], IchimokuSignal]
_EntryGateProvider = Callable[[int, Bias], Mapping[str, Any]]


def run_backtest(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    tf: str,
    params: IchimokuParams | None = None,
    min_bars: int | None = None,
    fee_bps: float = 0.0,
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
        fee_bps=fee_bps,
    )


def run_backtest_cartridge(
    candles: Sequence[Mapping[str, Any]],
    *,
    cartridge: Mapping[str, Any],
    symbol: str | None = None,
    tf: str | None = None,
    min_bars: int | None = None,
    fee_bps: float = 0.0,
    regime_tf: str | None = None,
    regime_htf: str | None = None,
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
    safe_regime_tf = validate_tf(regime_tf) if regime_tf is not None else None
    safe_regime_htf = validate_tf(regime_htf) if regime_htf is not None else None
    if _cartridge_requires_phase2_regime(cartridge) and safe_regime_tf is None:
        raise ValueError(
            f"cartridge {cartridge['id']} requires --regime-tf for Phase 2 regime hard veto"
        )
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
    cartridge_gate_provider = _entry_gate_provider(normalized, series=series, cartridge=cartridge)
    regime_gate_provider = (
        _regime_entry_gate_provider(
            candles,
            symbol=safe_symbol,
            regime_tf=safe_regime_tf,
            regime_htf=safe_regime_htf,
        )
        if safe_regime_tf is not None
        else None
    )
    entry_gate_provider = _combine_entry_gate_providers(
        cartridge_gate_provider,
        regime_gate_provider,
    )
    signal_provider = _signal_provider_for_cartridge(series, cartridge=cartridge)
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
            "and only block new entries. Phase 2 hard regime vetoes map the "
            "latest regime label with as_of <= the decision bar and never freeze "
            "exits. Execution uses next open when available, else current close."
        ),
        signal_provider=signal_provider,
        entry_gate_provider=entry_gate_provider,
        allowed_entry_sides=allowed_entry_sides,
        fee_bps=fee_bps,
    )
    if regime_gate_provider is not None:
        report["regime_gate"] = {
            "enabled": True,
            "tf": safe_regime_tf,
            "htf": safe_regime_htf,
            "policy": "TREND_BULL allows long only; TREND_BEAR allows short only; RANGE/VOLATILE/TRANSITION deny new entries; exits always allowed.",
        }
    _attach_cartridge_metadata(report, cartridge=cartridge, runnable=True)
    return report


def run_backtest_reference(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    tf: str,
    params: IchimokuParams | None = None,
    min_bars: int | None = None,
    fee_bps: float = 0.0,
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
        fee_bps=fee_bps,
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
    fee_bps: float = 0.0,
) -> dict[str, Any]:
    if min_bars <= 0:
        raise ValueError("min_bars must be positive")
    resolved_fee_bps = _nonnegative_float(fee_bps, "fee_bps")

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
            _normalize_entry_gate(entry_gate_provider(index, signal.bias))
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
                "components": _stable_mapping_values(signal.components),
                "features": dict(signal.features),
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
                fee_bps=resolved_fee_bps,
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
            fee_bps=resolved_fee_bps,
        )
        trades.append(trade)
        equity_points += float(trade["pnl_points"])
        peak_equity_points = max(peak_equity_points, equity_points)
        max_drawdown_points = max(max_drawdown_points, peak_equity_points - equity_points)

    trade_count = len(trades)
    winning_trades = sum(1 for trade in trades if float(trade["pnl_points"]) > 0)
    evaluated_bars = len(signal_trace)
    total_pnl_points = sum(float(trade["pnl_points"]) for trade in trades)
    total_fee_points = sum(float(trade.get("fee_points", 0.0)) for trade in trades)
    metrics = {
        "trade_count": trade_count,
        "win_rate": (winning_trades / trade_count) if trade_count else 0.0,
        "total_pnl_points": _stable_float(total_pnl_points),
        "max_drawdown_points": _stable_float(max_drawdown_points),
        "time_in_market": (bars_in_market / evaluated_bars) if evaluated_bars else 0.0,
        "bars_in_market": bars_in_market,
        "bias_counts": bias_counts,
        "final_bias": final_bias,
    }
    if entry_gate_provider is not None or allowed_entry_sides is not None:
        metrics["entry_gate_denied_count"] = sum(
            1
            for signal in signal_trace
            if signal["bias"] != "flat" and not signal["entry_gate"]["allowed"]
        )
    if resolved_fee_bps > 0:
        metrics["fee_bps"] = _stable_float(resolved_fee_bps)
        metrics["total_fee_points"] = _stable_float(total_fee_points)
        metrics["total_pnl_points_after_fees"] = _stable_float(
            total_pnl_points - total_fee_points
        )
        metrics["fee_adjusted_baseline_metric"] = "total_pnl_points_after_fees"
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
        "fee_bps": _stable_float(resolved_fee_bps),
        "fee_assumption": FEE_ASSUMPTION,
        "fee_model": FEE_MODEL,
        "naive": True,
        "model": MODEL_DESCRIPTION,
        "engine": engine,
        "lookahead_note": lookahead_note,
        "metrics": metrics,
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
    fee_bps: float = 0.0,
) -> dict[str, Any]:
    """Read stored OHLCV and return a backtest report."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    candles = read_candles(safe_symbol, safe_tf, aura_root_override=aura_root)
    windowed_candles = _window_candles(candles, max_bars=max_bars, since_ts_ms=since_ts_ms)
    report = run_backtest(
        windowed_candles,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
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
    fee_bps: float = 0.0,
    regime_tf: str | None = None,
    regime_htf: str | None = None,
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
        fee_bps=fee_bps,
        regime_tf=regime_tf,
        regime_htf=regime_htf,
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


def cartridge_oos_backtest_from_store(
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
    fee_bps: float = 0.0,
    regime_tf: str | None = None,
    regime_htf: str | None = None,
    oos_split: float = 0.7,
) -> dict[str, Any]:
    """Read stored OHLCV and return a chronological IS/OOS cartridge bake-off."""

    split_fraction = _split_fraction(oos_split)
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
    report = run_cartridge_oos_split(
        windowed_candles,
        cartridge=cartridge,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
        regime_tf=regime_tf,
        regime_htf=regime_htf,
        oos_split=split_fraction,
        cartridge_root=cartridge_root,
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


def run_cartridge_oos_split(
    candles: Sequence[Mapping[str, Any]],
    *,
    cartridge: Mapping[str, Any],
    symbol: str | None = None,
    tf: str | None = None,
    min_bars: int | None = None,
    fee_bps: float = 0.0,
    regime_tf: str | None = None,
    regime_htf: str | None = None,
    oos_split: float = 0.7,
    cartridge_root: str | Path = CARTRIDGE_ROOT,
) -> dict[str, Any]:
    """Run a pre-registered chronological IS/OOS cartridge bake-off."""

    split_fraction = _split_fraction(oos_split)
    safe_symbol = validate_symbol(symbol if symbol is not None else str(cartridge["symbol"]))
    safe_tf = validate_tf(tf if tf is not None else str(cartridge["tf"]))
    split_index = _chronological_split_index(len(candles), split_fraction)
    is_candles = list(candles[:split_index])
    oos_candles = list(candles[split_index:])
    candidate_is = run_backtest_cartridge(
        is_candles,
        cartridge=cartridge,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
        regime_tf=regime_tf,
        regime_htf=regime_htf,
    )
    candidate_oos = run_backtest_cartridge(
        oos_candles,
        cartridge=cartridge,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
        regime_tf=regime_tf,
        regime_htf=regime_htf,
    )
    baseline_is = _run_baseline_backtest(
        is_candles,
        cartridge=cartridge,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
        regime_tf=regime_tf,
        regime_htf=regime_htf,
        cartridge_root=cartridge_root,
    )
    baseline_oos = _run_baseline_backtest(
        oos_candles,
        cartridge=cartridge,
        symbol=safe_symbol,
        tf=safe_tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
        regime_tf=regime_tf,
        regime_htf=regime_htf,
        cartridge_root=cartridge_root,
    )
    kill_criteria = _mapping(cartridge, "kill_criteria")
    metric_name = str(kill_criteria["baseline_metric"])
    min_trades = int(kill_criteria["min_trades"])
    max_dd_points = float(kill_criteria["max_dd_points"])
    must_beat_baseline = bool(kill_criteria["must_beat_baseline"])
    is_gate = _oos_half_gate(
        candidate=candidate_is,
        baseline=baseline_is,
        metric_name=metric_name,
        min_trades=min_trades,
        max_dd_points=max_dd_points,
        must_beat_baseline=must_beat_baseline,
    )
    oos_gate = _oos_half_gate(
        candidate=candidate_oos,
        baseline=baseline_oos,
        metric_name=metric_name,
        min_trades=min_trades,
        max_dd_points=max_dd_points,
        must_beat_baseline=must_beat_baseline,
    )
    pass_oos_gate = bool(is_gate["passed"] and oos_gate["passed"])
    params = _params_from_cartridge(cartridge)
    report = {
        "schema": BACKTEST_REPORT_SCHEMA,
        "ok": bool(
            candidate_is.get("ok")
            and candidate_oos.get("ok")
            and baseline_is.get("ok")
            and baseline_oos.get("ok")
        ),
        "generated_at": utc_now_iso(),
        "symbol": safe_symbol,
        "tf": safe_tf,
        "candle_count": len(candles),
        "evaluated_bars": int(candidate_is["evaluated_bars"]) + int(candidate_oos["evaluated_bars"]),
        "min_bars": min_bars if min_bars is not None else params.minimum_candles,
        "params": params.to_dict(),
        "fee_bps": _stable_float(_nonnegative_float(fee_bps, "fee_bps")),
        "fee_assumption": FEE_ASSUMPTION,
        "fee_model": FEE_MODEL,
        "naive": True,
        "model": MODEL_DESCRIPTION,
        "engine": f"{CARTRIDGE_ENGINE}_oos_split_v1",
        "lookahead_note": (
            "Chronological IS/OOS bake-off. Split fraction is pre-registered "
            "before scoring; candidate and baseline are scored separately on "
            "the first in-sample slice and final out-of-sample slice."
        ),
        "metrics": {
            "is": candidate_is["metrics"],
            "oos": candidate_oos["metrics"],
        },
        "oos_split": {
            "enabled": True,
            "is_fraction": _stable_float(split_fraction),
            "oos_fraction": _stable_float(1.0 - split_fraction),
            "split_index": split_index,
            "is_candle_count": len(is_candles),
            "oos_candle_count": len(oos_candles),
            "baseline_ref": str(cartridge["baseline_ref"]),
            "baseline_metric": metric_name,
            "min_trades_per_half": min_trades,
            "must_beat_baseline": must_beat_baseline,
            "pass_oos_gate": pass_oos_gate,
            "is_gate": is_gate,
            "oos_gate": oos_gate,
        },
        "is": candidate_is,
        "oos": candidate_oos,
        "baseline": {
            "ref": str(cartridge["baseline_ref"]),
            "is": baseline_is,
            "oos": baseline_oos,
        },
    }
    if "regime_gate" in candidate_is or "regime_gate" in candidate_oos:
        report["regime_gate"] = candidate_is.get("regime_gate", candidate_oos.get("regime_gate"))
    if not report["ok"]:
        report["reason"] = "one_or_more_oos_split_reports_failed"
    _attach_cartridge_metadata(report, cartridge=cartridge, runnable=True)
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

    if cartridge.get("status") == "killed":
        reasons.append("status='killed' is not runnable")

    entry_mode = str(entry_rules["mode"])
    require_tk_state = str(entry_rules["require_tk_state"])
    exit_mode = str(exit_rules["mode"])
    regime_type = str(regime["type"])
    is_always_on = entry_mode == "always_on"
    is_tk_cloud_strong = (
        entry_mode == "tk_cloud_bias"
        and require_tk_state == "tk_cross_only"
        and exit_mode == "flat_on_rule_fail"
        and regime_type == "none"
        and not bool(entry_rules["require_chikou_confirmation"])
    )
    is_plain_tk_cross = (
        entry_mode == "tk_cross"
        and require_tk_state == "tk_cross_only"
        and exit_mode == "flat_on_rule_fail"
        and regime_type == "none"
        and not bool(entry_rules["require_chikou_confirmation"])
    )
    is_kumo_break = (
        entry_mode == "kumo_break"
        and require_tk_state == "none"
        and exit_mode == "flat_on_rule_fail"
        and regime_type == "none"
        and not bool(entry_rules["require_chikou_confirmation"])
    )
    is_kijun_bounce = (
        entry_mode == "kijun_bounce"
        and require_tk_state == "none"
        and exit_mode == "flat_on_rule_fail"
        and regime_type == "none"
        and bool(entry_rules["require_chikou_confirmation"])
        and entry_rules["chikou_mode"] == "close"
    )
    is_tenkan_bounce = (
        entry_mode == "tenkan_bounce"
        and require_tk_state == "none"
        and exit_mode == "flat_on_rule_fail"
        and regime_type == "none"
        and not bool(entry_rules["require_chikou_confirmation"])
        and entry_rules["chikou_mode"] == "close"
    )

    if not (
        is_always_on
        or is_tk_cloud_strong
        or is_plain_tk_cross
        or is_kumo_break
        or is_kijun_bounce
        or is_tenkan_bounce
    ):
        reasons.append(f"entry_rules.mode={entry_rules['mode']!r} is not wired")
    if entry_rules["require_close_vs_cloud"] != "above_for_long_below_for_short":
        reasons.append(
            "entry_rules.require_close_vs_cloud="
            f"{entry_rules['require_close_vs_cloud']!r} is not wired"
        )
    if is_always_on and require_tk_state != "tenkan_over_kijun_for_long_under_for_short":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if is_tk_cloud_strong and require_tk_state != "tk_cross_only":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if is_plain_tk_cross and require_tk_state != "tk_cross_only":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if is_kumo_break and require_tk_state != "none":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if is_kijun_bounce and require_tk_state != "none":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if is_tenkan_bounce and require_tk_state != "none":
        reasons.append(
            "entry_rules.require_tk_state="
            f"{entry_rules['require_tk_state']!r} is not wired"
        )
    if is_always_on and not bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=false is not wired")
    if is_tk_cloud_strong and bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=true is not wired")
    if is_plain_tk_cross and bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=true is not wired")
    if is_kumo_break and bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=true is not wired")
    if is_kijun_bounce and not bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=false is not wired")
    if is_tenkan_bounce and bool(entry_rules["require_chikou_confirmation"]):
        reasons.append("entry_rules.require_chikou_confirmation=true is not wired")
    if entry_rules["chikou_mode"] not in {"close", "strict"}:
        reasons.append(f"entry_rules.chikou_mode={entry_rules['chikou_mode']!r} is not wired")
    if "require_kijun_dip_setup" in entry_rules and not isinstance(
        entry_rules["require_kijun_dip_setup"],
        bool,
    ):
        reasons.append("entry_rules.require_kijun_dip_setup must be boolean")
    if "require_cloud_color_align" in entry_rules and not isinstance(
        entry_rules["require_cloud_color_align"],
        bool,
    ):
        reasons.append("entry_rules.require_cloud_color_align must be boolean")
    if "setup_bars" in entry_rules:
        setup_bars = entry_rules["setup_bars"]
        if not isinstance(setup_bars, int) or isinstance(setup_bars, bool) or setup_bars <= 0:
            reasons.append("entry_rules.setup_bars must be a positive integer")
    if bool(entry_rules.get("require_kijun_dip_setup", False)) and "setup_bars" not in entry_rules:
        reasons.append("entry_rules.setup_bars is required when require_kijun_dip_setup=true")
    if not is_tk_cloud_strong and (
        bool(entry_rules.get("require_kijun_dip_setup", False))
        or bool(entry_rules.get("require_cloud_color_align", False))
        or "setup_bars" in entry_rules
    ):
        reasons.append("TK-strong refinement entry flags are only wired for tk_cloud_bias")
    if is_always_on and exit_mode != "bias_flip":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if is_tk_cloud_strong and exit_mode != "flat_on_rule_fail":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if is_plain_tk_cross and exit_mode != "flat_on_rule_fail":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if is_kumo_break and exit_mode != "flat_on_rule_fail":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if is_kijun_bounce and exit_mode != "flat_on_rule_fail":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if is_tenkan_bounce and exit_mode != "flat_on_rule_fail":
        reasons.append(f"exit_rules.mode={exit_rules['mode']!r} is not wired")
    if not bool(exit_rules["close_on_flat"]):
        reasons.append("exit_rules.close_on_flat=false is not wired")
    if not bool(exit_rules["close_on_opposite"]):
        reasons.append("exit_rules.close_on_opposite=false is not wired")
    if exit_rules["max_bars_in_trade"] is not None:
        reasons.append("exit_rules.max_bars_in_trade is not wired")
    if regime_type not in {"none", "adx", "er", "cloud_thickness"}:
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


def compute_efficiency_ratio(
    candles: Sequence[Mapping[str, Any]],
    *,
    period: int,
) -> list[float | None]:
    """Compute Kaufman's Efficiency Ratio aligned to the input candles."""

    if period <= 0:
        raise ValueError("ER period must be positive")

    closes = [
        _finite_float(candle.get("close"), field_name=f"candles[{index}].close")
        for index, candle in enumerate(candles)
    ]
    er_values: list[float | None] = [None] * len(candles)
    for index in range(period, len(candles)):
        net_change = abs(closes[index] - closes[index - period])
        volatility = sum(
            abs(closes[inner_index] - closes[inner_index - 1])
            for inner_index in range(index - period + 1, index + 1)
        )
        er_values[index] = 0.0 if volatility <= 0 else net_change / volatility
    return er_values


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
    series: Any,
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

        def gate(index: int, side: Bias) -> Mapping[str, Any]:
            adx_value = adx_values[index]
            values = {"adx": _stable_float(adx_value), "period": period, "threshold": threshold}
            if adx_value is None:
                return {"allowed": False, "reason": "adx_unavailable", "values": values}
            if adx_value < float(threshold):
                return {"allowed": False, "reason": "adx_below_threshold", "values": values}
            return {"allowed": True, "reason": "adx_threshold_met", "values": values}

        return gate
    elif regime_type == "er":
        params = _mapping(regime, "params")
        period = _positive_int(params.get("period"), "regime.params.period")
        threshold = _positive_float(params.get("threshold"), "regime.params.threshold")
        er_values = compute_efficiency_ratio(candles, period=period)

        def gate(index: int, side: Bias) -> Mapping[str, Any]:
            er_value = er_values[index]
            values = {"er": _stable_float(er_value), "period": period, "threshold": threshold}
            if er_value is None:
                return {"allowed": False, "reason": "er_unavailable", "values": values}
            if er_value < float(threshold):
                return {"allowed": False, "reason": "er_below_threshold", "values": values}
            return {"allowed": True, "reason": "er_threshold_met", "values": values}

        return gate
    elif regime_type == "cloud_thickness":
        params = _mapping(regime, "params")
        min_pct = _positive_float(params.get("min_pct"), "regime.params.min_pct")
        thickness_values = _cloud_thickness_pct(series)

        def gate(index: int, side: Bias) -> Mapping[str, Any]:
            thickness_pct = thickness_values[index]
            values = {"thickness_pct": _stable_float(thickness_pct), "min_pct": min_pct}
            if thickness_pct is None:
                return {"allowed": False, "reason": "cloud_thickness_unavailable", "values": values}
            if thickness_pct < min_pct:
                return {"allowed": False, "reason": "cloud_thickness_below_min", "values": values}
            return {"allowed": True, "reason": "cloud_thickness_min_met", "values": values}

        return gate
    else:
        raise NotImplementedError(f"regime.type={regime_type!r} is not wired")


def _regime_entry_gate_provider(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    regime_tf: str,
    regime_htf: str | None,
) -> _EntryGateProvider:
    regime_candles = resample_1h_candles(candles, symbol=symbol, target_tf=regime_tf)
    htf_candles = (
        resample_1h_candles(candles, symbol=symbol, target_tf=regime_htf)
        if regime_htf is not None
        else None
    )
    params = RegimeParams(regime_tf=regime_tf, htf_tf=regime_htf)
    snapshots = classify_series(regime_candles, params=params, tf=regime_tf, htf_candles=htf_candles)
    snapshot_as_of = [
        int(snapshot.as_of)
        for snapshot in snapshots
        if snapshot.as_of is not None
    ]
    indexed_snapshots = [
        snapshot
        for snapshot in snapshots
        if snapshot.as_of is not None
    ]

    def gate(index: int, side: Bias) -> Mapping[str, Any]:
        if side == "flat":
            return {
                "allowed": True,
                "reason": "regime_not_applicable_flat_bias",
                "values": {},
            }
        bar_ts_ms = _candle_ts_ms(candles[index])
        snapshot_index = bisect_right(snapshot_as_of, bar_ts_ms) - 1
        if snapshot_index < 0:
            allowed, reasons = regime_allows(side, None)
            return {
                "allowed": allowed,
                "reason": reasons[0],
                "values": {
                    "side": side,
                    "state": None,
                    "as_of": None,
                    "reasons": reasons,
                },
            }

        snapshot = indexed_snapshots[snapshot_index]
        allowed, reasons = regime_allows(side, snapshot.state)
        return {
            "allowed": allowed,
            "reason": "regime_allows" if allowed else "regime_veto",
            "values": {
                "side": side,
                "state": snapshot.state.value,
                "as_of": snapshot.as_of,
                "tf": snapshot.tf,
                "confidence": _stable_float(snapshot.confidence),
                "reasons": reasons,
            },
        }

    return gate


def _combine_entry_gate_providers(
    cartridge_gate_provider: _EntryGateProvider | None,
    regime_gate_provider: _EntryGateProvider | None,
) -> _EntryGateProvider | None:
    if cartridge_gate_provider is None:
        return regime_gate_provider
    if regime_gate_provider is None:
        return cartridge_gate_provider

    def gate(index: int, side: Bias) -> Mapping[str, Any]:
        cartridge_gate = _normalize_entry_gate(cartridge_gate_provider(index, side))
        regime_gate = _normalize_entry_gate(regime_gate_provider(index, side))
        if not cartridge_gate["allowed"]:
            reason = cartridge_gate["reason"]
        elif not regime_gate["allowed"]:
            reason = regime_gate["reason"]
        else:
            reason = "entry_gates_passed"
        return {
            "allowed": cartridge_gate["allowed"] and regime_gate["allowed"],
            "reason": reason,
            "values": {
                "cartridge_gate": cartridge_gate,
                "regime_gate": regime_gate,
            },
        }

    return gate


def _cartridge_requires_phase2_regime(cartridge: Mapping[str, Any]) -> bool:
    return str(cartridge.get("id", "")) in _PHASE2_REGIME_REQUIRED_CARTRIDGES


def _run_baseline_backtest(
    candles: Sequence[Mapping[str, Any]],
    *,
    cartridge: Mapping[str, Any],
    symbol: str,
    tf: str,
    min_bars: int | None,
    fee_bps: float,
    regime_tf: str | None,
    regime_htf: str | None,
    cartridge_root: str | Path,
) -> dict[str, Any]:
    baseline_ref = str(cartridge["baseline_ref"])
    if baseline_ref == "ichimoku_v0":
        return run_backtest(
            candles,
            symbol=symbol,
            tf=tf,
            min_bars=min_bars,
            fee_bps=fee_bps,
        )

    baseline_cartridge = resolve_cartridge(
        cartridge_id=baseline_ref,
        cartridge_root=cartridge_root,
    )
    baseline_regime_tf = (
        regime_tf
        if baseline_ref == "ichi_v0_baseline" or _cartridge_requires_phase2_regime(baseline_cartridge)
        else None
    )
    baseline_regime_htf = regime_htf if baseline_regime_tf is not None else None
    return run_backtest_cartridge(
        candles,
        cartridge=baseline_cartridge,
        symbol=symbol,
        tf=tf,
        min_bars=min_bars,
        fee_bps=fee_bps,
        regime_tf=baseline_regime_tf,
        regime_htf=baseline_regime_htf,
    )


def _oos_half_gate(
    *,
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    metric_name: str,
    min_trades: int,
    max_dd_points: float,
    must_beat_baseline: bool,
) -> dict[str, Any]:
    candidate_metric = _metric_value(candidate, metric_name)
    baseline_metric = _metric_value(baseline, metric_name)
    trade_count = int(_mapping(candidate, "metrics")["trade_count"])
    max_drawdown_points = float(_mapping(candidate, "metrics")["max_drawdown_points"])
    min_trades_ok = trade_count >= min_trades
    max_dd_ok = max_drawdown_points <= max_dd_points
    beat_baseline = (
        _beats_baseline(metric_name, candidate_metric, baseline_metric)
        if must_beat_baseline
        else True
    )
    report_ok = bool(candidate.get("ok")) and bool(baseline.get("ok"))
    return {
        "passed": bool(report_ok and min_trades_ok and max_dd_ok and beat_baseline),
        "report_ok": report_ok,
        "metric": metric_name,
        "candidate_metric": _stable_float(candidate_metric),
        "baseline_metric": _stable_float(baseline_metric),
        "beat_baseline": beat_baseline,
        "trade_count": trade_count,
        "min_trades": min_trades,
        "min_trades_ok": min_trades_ok,
        "max_drawdown_points": _stable_float(max_drawdown_points),
        "max_dd_points": _stable_float(max_dd_points),
        "max_dd_ok": max_dd_ok,
    }


def _metric_value(report: Mapping[str, Any], metric_name: str) -> float:
    metrics = _mapping(report, "metrics")
    if metric_name in metrics:
        return float(metrics[metric_name])
    if metric_name == "total_pnl_points_after_fees" and "total_pnl_points" in metrics:
        return float(metrics["total_pnl_points"])
    raise ValueError(f"metric {metric_name!r} is not available in report")


def _beats_baseline(metric_name: str, candidate_metric: float, baseline_metric: float) -> bool:
    if metric_name == "max_drawdown_points":
        return candidate_metric < baseline_metric
    return candidate_metric > baseline_metric


def _split_fraction(value: float) -> float:
    fraction = _nonnegative_float(value, "oos_split")
    if fraction <= 0.0 or fraction >= 1.0:
        raise ValueError("--oos-split must be greater than 0 and less than 1")
    return fraction


def _chronological_split_index(candle_count: int, split_fraction: float) -> int:
    split_index = int(candle_count * split_fraction)
    if split_index <= 0 or split_index >= candle_count:
        raise ValueError(
            "oos split must leave at least one candle in both in-sample and out-of-sample halves"
        )
    return split_index


def _signal_provider_for_cartridge(
    series: Any,
    *,
    cartridge: Mapping[str, Any],
) -> _SignalProvider:
    entry_rules = _mapping(cartridge, "entry_rules")
    chikou_mode = str(entry_rules["chikou_mode"])
    if entry_rules["mode"] == "always_on":
        return lambda index: signal_from_series(
            series,
            index=index,
            chikou_mode=chikou_mode,  # type: ignore[arg-type]
        )
    if (
        entry_rules["mode"] == "tk_cloud_bias"
        and entry_rules["require_tk_state"] == "tk_cross_only"
    ):
        return lambda index: _tk_cloud_strong_signal_from_series(
            series,
            index=index,
            require_kijun_dip_setup=bool(entry_rules.get("require_kijun_dip_setup", False)),
            setup_bars=entry_rules.get("setup_bars"),
            require_cloud_color_align=bool(entry_rules.get("require_cloud_color_align", False)),
        )
    if (
        entry_rules["mode"] == "tk_cross"
        and entry_rules["require_tk_state"] == "tk_cross_only"
    ):
        return lambda index: _tk_cross_signal_from_series(series, index=index)
    if entry_rules["mode"] == "kumo_break":
        return lambda index: _kumo_break_signal_from_series(series, index=index)
    if entry_rules["mode"] == "kijun_bounce":
        return lambda index: _kijun_bounce_signal_from_series(series, index=index)
    if entry_rules["mode"] == "tenkan_bounce":
        return lambda index: _tenkan_bounce_signal_from_series(series, index=index)
    raise NotImplementedError(f"entry_rules.mode={entry_rules['mode']!r} is not wired")


def _tk_cloud_strong_signal_from_series(
    series: Any,
    *,
    index: int,
    require_kijun_dip_setup: bool = False,
    setup_bars: Any = None,
    require_cloud_color_align: bool = False,
) -> IchimokuSignal:
    if not series.points:
        return _empty_signal(series.params, "no_candles")
    if not series.ok:
        return _empty_signal(series.params, series.reason or "series_not_ready")
    if index <= 0:
        return _empty_signal(series.params, "missing_tk_cross_reference")

    point = series.points[index]
    previous = series.points[index - 1]
    required_components = (
        point.tenkan,
        point.kijun,
        point.senkou_span_a_displaced,
        point.senkou_span_b_displaced,
        previous.tenkan,
        previous.kijun,
    )
    if any(value is None for value in required_components):
        return _empty_signal(series.params, "missing_ichimoku_components")

    tenkan = _required_float(point.tenkan, "tenkan")
    kijun = _required_float(point.kijun, "kijun")
    previous_tenkan = _required_float(previous.tenkan, "previous_tenkan")
    previous_kijun = _required_float(previous.kijun, "previous_kijun")
    span_a = _required_float(point.senkou_span_a_displaced, "senkou_span_a_displaced")
    span_b = _required_float(point.senkou_span_b_displaced, "senkou_span_b_displaced")
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    close = point.close

    tk_bull_cross = previous_tenkan <= previous_kijun and tenkan > kijun
    tk_bear_cross = previous_tenkan >= previous_kijun and tenkan < kijun
    setup_window_bars = _positive_int(setup_bars, "entry_rules.setup_bars") if setup_bars is not None else 0
    kijun_dip_setup_long = True
    kijun_dip_setup_short = True
    if require_kijun_dip_setup:
        start_index = max(0, index - setup_window_bars)
        setup_points = series.points[start_index:index]
        kijun_dip_setup_long = any(
            setup_point.tenkan is not None
            and setup_point.kijun is not None
            and setup_point.tenkan <= setup_point.kijun
            for setup_point in setup_points
        )
        kijun_dip_setup_short = any(
            setup_point.tenkan is not None
            and setup_point.kijun is not None
            and setup_point.tenkan >= setup_point.kijun
            for setup_point in setup_points
        )
    cloud_color_bullish = span_a > span_b
    cloud_color_bearish = span_a < span_b
    cloud_color_long_ok = cloud_color_bullish if require_cloud_color_align else True
    cloud_color_short_ok = cloud_color_bearish if require_cloud_color_align else True
    features = {
        "has_cloud": True,
        "tk_bull_cross": tk_bull_cross,
        "tk_bear_cross": tk_bear_cross,
        "tenkan_above_cloud_top": tenkan > cloud_top,
        "kijun_above_cloud_top": kijun > cloud_top,
        "close_above_cloud": close > cloud_top,
        "tenkan_below_cloud_bottom": tenkan < cloud_bottom,
        "kijun_below_cloud_bottom": kijun < cloud_bottom,
        "close_below_cloud": close < cloud_bottom,
        "require_kijun_dip_setup": require_kijun_dip_setup,
        "kijun_dip_setup_long": kijun_dip_setup_long,
        "kijun_dip_setup_short": kijun_dip_setup_short,
        "require_cloud_color_align": require_cloud_color_align,
        "cloud_color_bullish": cloud_color_bullish,
        "cloud_color_bearish": cloud_color_bearish,
        "cloud_color_long_ok": cloud_color_long_ok,
        "cloud_color_short_ok": cloud_color_short_ok,
    }
    features["bullish_rule"] = (
        features["tk_bull_cross"]
        and features["tenkan_above_cloud_top"]
        and features["kijun_above_cloud_top"]
        and features["close_above_cloud"]
        and features["kijun_dip_setup_long"]
        and features["cloud_color_long_ok"]
    )
    features["bearish_rule"] = (
        features["tk_bear_cross"]
        and features["tenkan_below_cloud_bottom"]
        and features["kijun_below_cloud_bottom"]
        and features["close_below_cloud"]
        and features["kijun_dip_setup_short"]
        and features["cloud_color_short_ok"]
    )

    bias: Bias = "flat"
    if features["bullish_rule"]:
        bias = "long"
    elif features["bearish_rule"]:
        bias = "short"

    components = {
        "close": close,
        "cloud_top": cloud_top,
        "cloud_bottom": cloud_bottom,
        "tenkan": tenkan,
        "kijun": kijun,
        "previous_tenkan": previous_tenkan,
        "previous_kijun": previous_kijun,
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": span_a,
        "senkou_span_b_displaced": span_b,
        "setup_bars": setup_window_bars if setup_bars is not None else None,
        "chikou_mode": "close",
    }
    return IchimokuSignal(
        ok=True,
        reason=None,
        bias=bias,
        index=point.index,
        ts_ms=point.ts_ms,
        params=series.params,
        components=components,
        features=features,
    )


def _tk_cross_signal_from_series(series: Any, *, index: int) -> IchimokuSignal:
    if not series.points:
        return _empty_signal(series.params, "no_candles")
    if not series.ok:
        return _empty_signal(series.params, series.reason or "series_not_ready")
    if index <= 0:
        return _empty_signal(series.params, "missing_tk_cross_reference")

    point = series.points[index]
    previous = series.points[index - 1]
    required_components = (
        point.tenkan,
        point.kijun,
        point.senkou_span_a_displaced,
        point.senkou_span_b_displaced,
        previous.tenkan,
        previous.kijun,
    )
    if any(value is None for value in required_components):
        return _empty_signal(series.params, "missing_ichimoku_components")

    tenkan = _required_float(point.tenkan, "tenkan")
    kijun = _required_float(point.kijun, "kijun")
    previous_tenkan = _required_float(previous.tenkan, "previous_tenkan")
    previous_kijun = _required_float(previous.kijun, "previous_kijun")
    span_a = _required_float(point.senkou_span_a_displaced, "senkou_span_a_displaced")
    span_b = _required_float(point.senkou_span_b_displaced, "senkou_span_b_displaced")
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    close = point.close

    features = {
        "has_cloud": True,
        "tk_bull_cross": previous_tenkan <= previous_kijun and tenkan > kijun,
        "tk_bear_cross": previous_tenkan >= previous_kijun and tenkan < kijun,
        "close_above_cloud": close > cloud_top,
        "close_below_cloud": close < cloud_bottom,
    }
    features["bullish_rule"] = features["tk_bull_cross"] and features["close_above_cloud"]
    features["bearish_rule"] = features["tk_bear_cross"] and features["close_below_cloud"]

    bias: Bias = "flat"
    if features["bullish_rule"]:
        bias = "long"
    elif features["bearish_rule"]:
        bias = "short"

    components = {
        "close": close,
        "cloud_top": cloud_top,
        "cloud_bottom": cloud_bottom,
        "tenkan": tenkan,
        "kijun": kijun,
        "previous_tenkan": previous_tenkan,
        "previous_kijun": previous_kijun,
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": span_a,
        "senkou_span_b_displaced": span_b,
        "chikou_mode": "close",
    }
    return IchimokuSignal(
        ok=True,
        reason=None,
        bias=bias,
        index=point.index,
        ts_ms=point.ts_ms,
        params=series.params,
        components=components,
        features=features,
    )


def _kumo_break_signal_from_series(series: Any, *, index: int) -> IchimokuSignal:
    if not series.points:
        return _empty_signal(series.params, "no_candles")
    if not series.ok:
        return _empty_signal(series.params, series.reason or "series_not_ready")
    if index <= 0:
        return _empty_signal(series.params, "missing_kumo_break_reference")

    point = series.points[index]
    previous = series.points[index - 1]
    required_components = (
        point.senkou_span_a_displaced,
        point.senkou_span_b_displaced,
        previous.senkou_span_a_displaced,
        previous.senkou_span_b_displaced,
    )
    if any(value is None for value in required_components):
        return _empty_signal(series.params, "missing_ichimoku_components")

    span_a = _required_float(point.senkou_span_a_displaced, "senkou_span_a_displaced")
    span_b = _required_float(point.senkou_span_b_displaced, "senkou_span_b_displaced")
    previous_span_a = _required_float(
        previous.senkou_span_a_displaced,
        "previous_senkou_span_a_displaced",
    )
    previous_span_b = _required_float(
        previous.senkou_span_b_displaced,
        "previous_senkou_span_b_displaced",
    )
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    previous_cloud_top = max(previous_span_a, previous_span_b)
    previous_cloud_bottom = min(previous_span_a, previous_span_b)
    close = point.close
    previous_close = previous.close

    features = {
        "has_cloud": True,
        "previous_close_at_or_below_cloud_top": previous_close <= previous_cloud_top,
        "close_above_cloud": close > cloud_top,
        "previous_close_at_or_above_cloud_bottom": previous_close >= previous_cloud_bottom,
        "close_below_cloud": close < cloud_bottom,
    }
    features["bullish_rule"] = (
        features["previous_close_at_or_below_cloud_top"] and features["close_above_cloud"]
    )
    features["bearish_rule"] = (
        features["previous_close_at_or_above_cloud_bottom"] and features["close_below_cloud"]
    )

    bias: Bias = "flat"
    if features["bullish_rule"]:
        bias = "long"
    elif features["bearish_rule"]:
        bias = "short"

    components = {
        "close": close,
        "previous_close": previous_close,
        "cloud_top": cloud_top,
        "cloud_bottom": cloud_bottom,
        "previous_cloud_top": previous_cloud_top,
        "previous_cloud_bottom": previous_cloud_bottom,
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": span_a,
        "senkou_span_b_displaced": span_b,
        "previous_senkou_span_a_displaced": previous_span_a,
        "previous_senkou_span_b_displaced": previous_span_b,
        "chikou_mode": "close",
    }
    return IchimokuSignal(
        ok=True,
        reason=None,
        bias=bias,
        index=point.index,
        ts_ms=point.ts_ms,
        params=series.params,
        components=components,
        features=features,
    )


def _kijun_bounce_signal_from_series(series: Any, *, index: int) -> IchimokuSignal:
    if not series.points:
        return _empty_signal(series.params, "no_candles")
    if not series.ok:
        return _empty_signal(series.params, series.reason or "series_not_ready")
    if index <= 0:
        return _empty_signal(series.params, "missing_kijun_bounce_reference")

    point = series.points[index]
    previous = series.points[index - 1]
    reference_index = point.index - series.params.displacement
    if reference_index < 0:
        return _empty_signal(series.params, "missing_chikou_reference")

    reference_point = series.points[reference_index]
    required_components = (
        point.kijun,
        point.senkou_span_a_displaced,
        point.senkou_span_b_displaced,
        previous.kijun,
    )
    if any(value is None for value in required_components):
        return _empty_signal(series.params, "missing_ichimoku_components")

    kijun = _required_float(point.kijun, "kijun")
    previous_kijun = _required_float(previous.kijun, "previous_kijun")
    span_a = _required_float(point.senkou_span_a_displaced, "senkou_span_a_displaced")
    span_b = _required_float(point.senkou_span_b_displaced, "senkou_span_b_displaced")
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    close = point.close
    previous_close = previous.close
    reference_close = reference_point.close
    chikou_above_reference = close > reference_close
    chikou_below_reference = close < reference_close
    features = {
        "has_cloud": True,
        "close_crossed_above_kijun": previous_close <= previous_kijun and close > kijun,
        "close_crossed_below_kijun": previous_close >= previous_kijun and close < kijun,
        "close_above_cloud": close > cloud_top,
        "close_below_cloud": close < cloud_bottom,
        "chikou_above_reference": chikou_above_reference,
        "chikou_below_reference": chikou_below_reference,
        "chikou_mode_close": True,
        "chikou_mode_strict": False,
    }
    features["bullish_rule"] = (
        features["close_crossed_above_kijun"]
        and features["close_above_cloud"]
        and features["chikou_above_reference"]
    )
    features["bearish_rule"] = (
        features["close_crossed_below_kijun"]
        and features["close_below_cloud"]
        and features["chikou_below_reference"]
    )

    bias: Bias = "flat"
    if features["bullish_rule"]:
        bias = "long"
    elif features["bearish_rule"]:
        bias = "short"

    components = {
        "close": close,
        "previous_close": previous_close,
        "cloud_top": cloud_top,
        "cloud_bottom": cloud_bottom,
        "kijun": kijun,
        "previous_kijun": previous_kijun,
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": span_a,
        "senkou_span_b_displaced": span_b,
        "chikou_value": close,
        "chikou_mode": "close",
        "chikou_reference_index": reference_index,
        "chikou_reference_close": reference_close,
    }
    return IchimokuSignal(
        ok=True,
        reason=None,
        bias=bias,
        index=point.index,
        ts_ms=point.ts_ms,
        params=series.params,
        components=components,
        features=features,
    )


def _tenkan_bounce_signal_from_series(series: Any, *, index: int) -> IchimokuSignal:
    if not series.points:
        return _empty_signal(series.params, "no_candles")
    if not series.ok:
        return _empty_signal(series.params, series.reason or "series_not_ready")
    if index <= 0:
        return _empty_signal(series.params, "missing_tenkan_bounce_reference")

    point = series.points[index]
    previous = series.points[index - 1]
    required_components = (
        point.tenkan,
        point.senkou_span_a_displaced,
        point.senkou_span_b_displaced,
        previous.tenkan,
    )
    if any(value is None for value in required_components):
        return _empty_signal(series.params, "missing_ichimoku_components")

    tenkan = _required_float(point.tenkan, "tenkan")
    previous_tenkan = _required_float(previous.tenkan, "previous_tenkan")
    span_a = _required_float(point.senkou_span_a_displaced, "senkou_span_a_displaced")
    span_b = _required_float(point.senkou_span_b_displaced, "senkou_span_b_displaced")
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    close = point.close
    previous_close = previous.close
    features = {
        "has_cloud": True,
        "close_crossed_above_tenkan": previous_close <= previous_tenkan and close > tenkan,
        "close_crossed_below_tenkan": previous_close >= previous_tenkan and close < tenkan,
        "close_above_cloud": close > cloud_top,
        "close_below_cloud": close < cloud_bottom,
    }
    features["bullish_rule"] = (
        features["close_crossed_above_tenkan"] and features["close_above_cloud"]
    )
    features["bearish_rule"] = (
        features["close_crossed_below_tenkan"] and features["close_below_cloud"]
    )

    bias: Bias = "flat"
    if features["bullish_rule"]:
        bias = "long"
    elif features["bearish_rule"]:
        bias = "short"

    components = {
        "close": close,
        "previous_close": previous_close,
        "cloud_top": cloud_top,
        "cloud_bottom": cloud_bottom,
        "tenkan": tenkan,
        "previous_tenkan": previous_tenkan,
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": span_a,
        "senkou_span_b_displaced": span_b,
        "chikou_mode": "close",
    }
    return IchimokuSignal(
        ok=True,
        reason=None,
        bias=bias,
        index=point.index,
        ts_ms=point.ts_ms,
        params=series.params,
        components=components,
        features=features,
    )


def _empty_signal(params: IchimokuParams, reason: str) -> IchimokuSignal:
    return IchimokuSignal(
        ok=False,
        reason=reason,
        bias="flat",
        index=None,
        ts_ms=None,
        params=params,
        components={},
        features={},
    )


def _cloud_thickness_pct(series: Any) -> list[float | None]:
    values: list[float | None] = []
    for point in series.points:
        span_a = point.senkou_span_a_displaced
        span_b = point.senkou_span_b_displaced
        close = point.close
        if span_a is None or span_b is None or close <= 0:
            values.append(None)
            continue
        cloud_top = max(span_a, span_b)
        cloud_bottom = min(span_a, span_b)
        values.append(((cloud_top - cloud_bottom) / close) * 100)
    return values


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


def _nonnegative_float(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _required_float(value: float | None, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required")
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
    fee_bps: float,
) -> dict[str, Any]:
    direction = int(position["direction"])
    entry_price = float(position["entry_price"])
    exit_price = float(exit_execution["price"])
    pnl_points = (exit_price - entry_price) * direction
    fee_points = (fee_bps / 10_000.0) * (entry_price + exit_price)
    trade = {
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
    if fee_bps > 0:
        trade["fee_bps"] = _stable_float(fee_bps)
        trade["fee_points"] = _stable_float(fee_points)
        trade["pnl_points_after_fees"] = _stable_float(pnl_points - fee_points)
    return trade


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
