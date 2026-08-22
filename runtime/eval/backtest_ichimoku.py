"""Naive paper-only backtest harness for Ichimoku v0 bias.

This module is intentionally thin: it reuses ``runtime.brain.ichimoku`` for all
indicator math and never calls Kraken, systemd, or any constellation path.

Lookahead note
--------------
For each evaluated candle index, the signal is computed from
``candles[: index + 1]`` only. The brain's displaced cloud values come from raw
Tenkan/Kijun/Senkou values calculated 26 bars in the past, and the Chikou rule
compares the current close to ``close[t-26]`` as implemented in
``runtime.brain.ichimoku``. The backtest therefore does not use future candles
for signal formation. The only future price used is the deliberately naive
execution assumption: decisions at bar ``t`` execute at bar ``t+1`` open when
available, otherwise at bar ``t`` close.
"""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
import json
from typing import Any, Mapping, Sequence

from runtime.brain import compute_ichimoku, signal_from_series
from runtime.brain.types import Bias, IchimokuParams
from runtime.market import ohlcv_path, read_candles, validate_symbol, validate_tf


BACKTEST_REPORT_SCHEMA = "aura.backtest_report.v1"
BACKTEST_TRADE_SCHEMA = "aura.backtest_trade.v1"
FEE_ASSUMPTION = 0
MODEL_DESCRIPTION = (
    "naive_v0: one position at a time, one unit notional in price points, "
    "next-bar-open execution when available else current close, no leverage, "
    "no fees, no slippage"
)

_DIRECTION_BY_BIAS: dict[Bias, int] = {"long": 1, "short": -1, "flat": 0}
_BIAS_BY_DIRECTION = {1: "long", -1: "short"}


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
    if resolved_min_bars <= 0:
        raise ValueError("min_bars must be positive")

    normalized = [_normalize_candle(index, candle) for index, candle in enumerate(candles)]
    start_index = resolved_min_bars - 1
    bias_counts: dict[str, int] = {"long": 0, "short": 0, "flat": 0}
    signal_trace: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    equity_points = 0.0
    peak_equity_points = 0.0
    max_drawdown_points = 0.0
    bars_in_market = 0
    final_bias: Bias = "flat"
    position: dict[str, Any] | None = None

    for index in range(start_index, len(normalized)):
        signal = signal_for_closed_bar(candles, index=index, params=resolved_params)
        final_bias = signal.bias
        bias_counts[signal.bias] += 1
        desired_direction = _DIRECTION_BY_BIAS[signal.bias]
        execution = _execution(normalized, index)
        signal_trace.append(
            {
                "index": index,
                "ts_ms": normalized[index]["ts_ms"],
                "ok": signal.ok,
                "reason": signal.reason,
                "bias": signal.bias,
                "execution_index": execution["index"],
                "execution_price": _stable_float(execution["price"]),
                "execution_basis": execution["basis"],
            }
        )

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

        if desired_direction != 0 and position is None:
            position = _open_position(
                direction=desired_direction,
                entry_execution=execution,
                entry_reason=f"bias_{signal.bias}",
            )

        if position is not None:
            bars_in_market += 1

    if position is not None and normalized:
        final_execution = {
            "index": len(normalized) - 1,
            "ts_ms": normalized[-1]["ts_ms"],
            "price": normalized[-1]["close"],
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
        "symbol": safe_symbol,
        "tf": safe_tf,
        "candle_count": len(normalized),
        "evaluated_bars": evaluated_bars,
        "min_bars": resolved_min_bars,
        "params": resolved_params.to_dict(),
        "fee_assumption": FEE_ASSUMPTION,
        "naive": True,
        "model": MODEL_DESCRIPTION,
        "lookahead_note": (
            "Signals are recomputed from candles[:index+1]. Displaced spans use "
            "past raw Ichimoku values, and Chikou compares current close to "
            "close[t-26] per runtime.brain.ichimoku. Execution uses next open "
            "when available, else current close."
        ),
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
) -> dict[str, Any]:
    """Read stored OHLCV and return a backtest report."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    candles = read_candles(safe_symbol, safe_tf, aura_root_override=aura_root)
    report = run_backtest(candles, symbol=safe_symbol, tf=safe_tf, min_bars=min_bars)
    report["market_path"] = str(ohlcv_path(safe_symbol, safe_tf, aura_root_override=aura_root))
    return report


def signal_for_closed_bar(
    candles: Sequence[Mapping[str, Any]],
    *,
    index: int,
    params: IchimokuParams | None = None,
) -> Any:
    """Compute the signal at ``index`` using no candles after ``index``."""

    if index < 0:
        raise ValueError("index must be non-negative")
    if index >= len(candles):
        raise ValueError("index out of range")
    resolved_params = params if params is not None else IchimokuParams()
    series = compute_ichimoku(candles[: index + 1], params=resolved_params)
    return signal_from_series(series)


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


def _stable_float(value: float) -> float:
    return round(float(value), 10)
