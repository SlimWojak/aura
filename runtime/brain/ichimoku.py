"""Deterministic Ichimoku v0 brain.

Constants are the standard Ichimoku settings:

- Tenkan-sen / conversion line: midpoint of highest high and lowest low over 9 bars.
- Kijun-sen / base line: midpoint of highest high and lowest low over 26 bars.
- Senkou Span A: midpoint of Tenkan and Kijun, plotted 26 bars ahead.
- Senkou Span B: midpoint of highest high and lowest low over 52 bars, plotted 26 bars ahead.
- Chikou Span: close plotted 26 bars back.

Signal policy v0 is a boring, testable hypothesis rather than a claimed edge.
At the latest stored candle, Aura treats the JSONL row as the latest closed bar
and compares price with the cloud formed by the displaced spans at that same
index:

- ``long`` when close is above the cloud top, Tenkan is above Kijun, and the
  current close (the Chikou value plotted 26 bars back) is above close[t-26].
- ``short`` when close is below the cloud bottom, Tenkan is below Kijun, and the
  current close is below close[t-26].
- ``flat`` otherwise.

The output includes raw spans, chart-displaced spans, and boolean feature flags
so eval can retune the rule later without rewriting the math.
"""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

from runtime.brain.types import IchimokuParams, IchimokuPoint, IchimokuSeries, IchimokuSignal


DEFAULT_PARAMS = IchimokuParams()


def compute_ichimoku(
    candles: Sequence[Mapping[str, Any]],
    *,
    params: IchimokuParams = DEFAULT_PARAMS,
) -> IchimokuSeries:
    """Compute Ichimoku rows from OHLC candles.

    The function is pure and does not read files or call venues. It computes
    partial rows even when there is not enough history for a valid latest-bar
    signal, returning ``ok=False`` with an explicit reason until at least
    ``senkou_b + displacement`` candles are present.
    """

    normalized = [_normalized_candle(index, candle) for index, candle in enumerate(candles)]
    highs = [row["high"] for row in normalized]
    lows = [row["low"] for row in normalized]
    closes = [row["close"] for row in normalized]

    tenkan_values = [_midpoint(highs, lows, index, params.tenkan) for index in range(len(candles))]
    kijun_values = [_midpoint(highs, lows, index, params.kijun) for index in range(len(candles))]
    span_a_raw = [
        _average_or_none(tenkan_values[index], kijun_values[index]) for index in range(len(candles))
    ]
    span_b_raw = [_midpoint(highs, lows, index, params.senkou_b) for index in range(len(candles))]

    points: list[IchimokuPoint] = []
    for index, row in enumerate(normalized):
        displaced_index = index - params.displacement
        chikou_source_index = index + params.displacement
        points.append(
            IchimokuPoint(
                index=index,
                ts_ms=row["ts_ms"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                tenkan=tenkan_values[index],
                kijun=kijun_values[index],
                senkou_span_a_raw=span_a_raw[index],
                senkou_span_b_raw=span_b_raw[index],
                senkou_span_a_displaced=span_a_raw[displaced_index]
                if displaced_index >= 0
                else None,
                senkou_span_b_displaced=span_b_raw[displaced_index]
                if displaced_index >= 0
                else None,
                chikou_span_displaced_back=closes[chikou_source_index]
                if chikou_source_index < len(closes)
                else None,
            )
        )

    reason = None
    ok = True
    if len(candles) < params.minimum_candles:
        ok = False
        reason = (
            "insufficient_history: "
            f"need at least {params.minimum_candles} candles, got {len(candles)}"
        )

    return IchimokuSeries(ok=ok, reason=reason, params=params, points=tuple(points))


def signal_from_series(series: IchimokuSeries, *, index: int | None = None) -> IchimokuSignal:
    """Return the latest closed-bar Ichimoku v0 signal."""

    if not series.points:
        return _empty_signal(series.params, "no_candles")
    if not series.ok:
        return _empty_signal(series.params, series.reason or "series_not_ready")

    point = series.points[index] if index is not None else series.points[-1]
    reference_index = point.index - series.params.displacement
    if reference_index < 0:
        return _empty_signal(series.params, "missing_chikou_reference")

    reference_close = series.points[reference_index].close
    required_components = (
        point.tenkan,
        point.kijun,
        point.senkou_span_a_displaced,
        point.senkou_span_b_displaced,
    )
    if any(value is None for value in required_components):
        return _empty_signal(series.params, "missing_ichimoku_components")

    span_a = _required_float(point.senkou_span_a_displaced, "senkou_span_a_displaced")
    span_b = _required_float(point.senkou_span_b_displaced, "senkou_span_b_displaced")
    tenkan = _required_float(point.tenkan, "tenkan")
    kijun = _required_float(point.kijun, "kijun")
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    close = point.close

    features = {
        "has_cloud": True,
        "close_above_cloud": close > cloud_top,
        "close_below_cloud": close < cloud_bottom,
        "tenkan_above_kijun": tenkan > kijun,
        "tenkan_below_kijun": tenkan < kijun,
        "chikou_above_reference": close > reference_close,
        "chikou_below_reference": close < reference_close,
    }
    features["bullish_rule"] = (
        features["close_above_cloud"]
        and features["tenkan_above_kijun"]
        and features["chikou_above_reference"]
    )
    features["bearish_rule"] = (
        features["close_below_cloud"]
        and features["tenkan_below_kijun"]
        and features["chikou_below_reference"]
    )

    bias = "flat"
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
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": span_a,
        "senkou_span_b_displaced": span_b,
        "chikou_value": close,
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


def latest_signal(
    candles: Sequence[Mapping[str, Any]],
    *,
    params: IchimokuParams = DEFAULT_PARAMS,
) -> IchimokuSignal:
    """Convenience wrapper for computing the series and latest signal."""

    return signal_from_series(compute_ichimoku(candles, params=params))


def _normalized_candle(index: int, candle: Mapping[str, Any]) -> dict[str, float | int | None]:
    return {
        "ts_ms": _optional_int(candle.get("ts_ms")),
        "high": _finite_float(candle.get("high"), field_name=f"candles[{index}].high"),
        "low": _finite_float(candle.get("low"), field_name=f"candles[{index}].low"),
        "close": _finite_float(candle.get("close"), field_name=f"candles[{index}].close"),
    }


def _midpoint(highs: Sequence[float], lows: Sequence[float], index: int, period: int) -> float | None:
    if period <= 0:
        raise ValueError("Ichimoku periods must be positive")
    if index + 1 < period:
        return None
    start = index + 1 - period
    return (max(highs[start : index + 1]) + min(lows[start : index + 1])) / 2.0


def _average_or_none(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return (left + right) / 2.0


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


def _required_float(value: float | None, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required")
    return value
