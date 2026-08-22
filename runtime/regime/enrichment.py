"""Thin Aura-native enrichment features from stored OHLCV.

The builders in this module are deliberately small and falsifiable. They do not
implement a full ICT stack, do not read live venues, and only consume stored
OHLCV candles that the caller already loaded.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, Mapping, Sequence

from runtime.regime.resample import HOUR_MS, resample_1h_candles


FvgSide = Literal["bullish", "bearish"]
DrSide = Literal["discount", "equilibrium", "premium"]

TF_DURATION_MS = {
    "1h": HOUR_MS,
    "4h": 4 * HOUR_MS,
    "1d": 24 * HOUR_MS,
}


@dataclass(frozen=True, slots=True)
class DealingRange:
    """Latest confirmed daily swing-high/swing-low range."""

    low: float
    high: float
    midpoint: float
    swing_low_ts_ms: int
    swing_high_ts_ms: int

    @property
    def width(self) -> float:
        return self.high - self.low


@dataclass(frozen=True, slots=True)
class FairValueGap:
    """Classic 3-candle fair value gap on one higher timeframe."""

    tf: str
    side: FvgSide
    lower: float
    upper: float
    detected_ts_ms: int

    def contains(self, price: float) -> bool:
        return self.lower <= price <= self.upper


def resample_for_enrichment(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    source_tf: str,
    target_tf: str,
) -> list[dict[str, Any]]:
    """Return complete target-TF candles from stored candles."""

    if source_tf == target_tf:
        return [_normalized_candle(index, candle, tf=target_tf) for index, candle in enumerate(candles)]
    if source_tf != "1h":
        raise ValueError("enrichment resampling currently requires stored 1h candles")
    return resample_1h_candles(candles, symbol=symbol, target_tf=target_tf)


def align_daily_dealing_ranges(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    source_tf: str,
) -> list[DealingRange | None]:
    """Align daily dealing ranges to source candles without HTF lookahead.

    A daily swing high/low is confirmed only after the next daily candle closes:
    ``high[j] > high[j-1] and high[j] > high[j+1]`` for swing highs, and the
    symmetric strict rule for lows. The active dealing range is the latest
    confirmed swing high paired with the latest confirmed swing low.
    """

    daily = resample_for_enrichment(candles, symbol=symbol, source_tf=source_tf, target_tf="1d")
    daily_states = daily_dealing_range_series(daily)
    return _align_htf_states(
        candles,
        source_tf=source_tf,
        htf_candles=daily,
        htf_tf="1d",
        states=daily_states,
    )


def daily_dealing_range_series(candles: Sequence[Mapping[str, Any]]) -> list[DealingRange | None]:
    """Build daily dealing range states aligned to completed daily candles."""

    rows = [_normalized_candle(index, candle, tf="1d") for index, candle in enumerate(candles)]
    states: list[DealingRange | None] = []
    latest_high: tuple[float, int] | None = None
    latest_low: tuple[float, int] | None = None
    for index in range(len(rows)):
        candidate = index - 1
        if candidate > 0:
            left = rows[candidate - 1]
            center = rows[candidate]
            right = rows[candidate + 1]
            if center["high"] > left["high"] and center["high"] > right["high"]:
                latest_high = (center["high"], center["ts_ms"])
            if center["low"] < left["low"] and center["low"] < right["low"]:
                latest_low = (center["low"], center["ts_ms"])
        states.append(_dealing_range_from_swings(latest_low, latest_high))
    return states


def dealing_range_side(close: float, dealing_range: DealingRange | None) -> DrSide | None:
    """Classify close into daily premium/discount/equilibrium."""

    if dealing_range is None:
        return None
    if close > dealing_range.midpoint:
        return "premium"
    if close < dealing_range.midpoint:
        return "discount"
    return "equilibrium"


def dealing_range_position(close: float, dealing_range: DealingRange | None) -> float | None:
    """Return signed position where low=-1, midpoint=0, high=+1."""

    if dealing_range is None or dealing_range.width <= 0:
        return None
    return (close - dealing_range.midpoint) / (dealing_range.width / 2.0)


def align_latest_fvg(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    source_tf: str,
    target_tf: str,
) -> list[FairValueGap | None]:
    """Align the latest confirmed target-TF FVG to source candles."""

    htf_candles = resample_for_enrichment(candles, symbol=symbol, source_tf=source_tf, target_tf=target_tf)
    gap_states = latest_fvg_series(htf_candles, tf=target_tf)
    return _align_htf_states(
        candles,
        source_tf=source_tf,
        htf_candles=htf_candles,
        htf_tf=target_tf,
        states=gap_states,
    )


def latest_fvg_series(candles: Sequence[Mapping[str, Any]], *, tf: str) -> list[FairValueGap | None]:
    """Return the latest classic 3-candle FVG after each completed candle."""

    rows = [_normalized_candle(index, candle, tf=tf) for index, candle in enumerate(candles)]
    latest: FairValueGap | None = None
    states: list[FairValueGap | None] = []
    for index, row in enumerate(rows):
        if index >= 2:
            left = rows[index - 2]
            if row["low"] > left["high"]:
                latest = FairValueGap(
                    tf=tf,
                    side="bullish",
                    lower=left["high"],
                    upper=row["low"],
                    detected_ts_ms=row["ts_ms"],
                )
            elif row["high"] < left["low"]:
                latest = FairValueGap(
                    tf=tf,
                    side="bearish",
                    lower=row["high"],
                    upper=left["low"],
                    detected_ts_ms=row["ts_ms"],
                )
        states.append(latest)
    return states


def fvg_distance_atr(close: float, gap: FairValueGap | None, atr: float | None) -> float | None:
    """Distance from close to the latest FVG edge, ATR-normalized."""

    if gap is None or atr is None or atr <= 0:
        return None
    if gap.contains(close):
        return 0.0
    if close < gap.lower:
        return (gap.lower - close) / atr
    return (close - gap.upper) / atr


def chikou_clears_dealing_range(
    closes: Sequence[float],
    ranges: Sequence[DealingRange | None],
    *,
    index: int,
    displacement: int,
) -> bool | None:
    """Return whether current close clears the Daily DR at its Chikou plot bar."""

    reference_index = index - displacement
    if reference_index < 0:
        return None
    dealing_range = ranges[reference_index]
    if dealing_range is None:
        return None
    close = closes[index]
    return close > dealing_range.high or close < dealing_range.low


def chikou_dealing_range_clearance_atr(
    closes: Sequence[float],
    ranges: Sequence[DealingRange | None],
    *,
    index: int,
    displacement: int,
    atr: float | None,
) -> float | None:
    """Signed ATR clearance of current close beyond the Chikou-reference DR."""

    reference_index = index - displacement
    if reference_index < 0 or atr is None or atr <= 0:
        return None
    dealing_range = ranges[reference_index]
    if dealing_range is None:
        return None
    close = closes[index]
    if close > dealing_range.high:
        return (close - dealing_range.high) / atr
    if close < dealing_range.low:
        return (close - dealing_range.low) / atr
    return 0.0


def flat_spanb_overlaps_fvg(
    *,
    span_b: float | None,
    flat_spanb_bars: int | None,
    flat_n: int,
    gap: FairValueGap | None,
) -> bool:
    """Return whether the lookahead-safe displaced flat Span B sits in the FVG."""

    if span_b is None or flat_spanb_bars is None or gap is None:
        return False
    return flat_spanb_bars >= flat_n and gap.lower <= span_b <= gap.upper


def _align_htf_states(
    source_candles: Sequence[Mapping[str, Any]],
    *,
    source_tf: str,
    htf_candles: Sequence[Mapping[str, Any]],
    htf_tf: str,
    states: Sequence[Any],
) -> list[Any]:
    source_duration_ms = _duration_ms(source_tf)
    htf_duration_ms = _duration_ms(htf_tf)
    htf_close_times = [int(candle["ts_ms"]) + htf_duration_ms for candle in htf_candles]
    aligned = []
    for candle in source_candles:
        source_close_ms = int(candle["ts_ms"]) + source_duration_ms
        htf_index = bisect_right(htf_close_times, source_close_ms) - 1
        aligned.append(None if htf_index < 0 else states[htf_index])
    return aligned


def _dealing_range_from_swings(
    latest_low: tuple[float, int] | None,
    latest_high: tuple[float, int] | None,
) -> DealingRange | None:
    if latest_low is None or latest_high is None:
        return None
    low, low_ts_ms = latest_low
    high, high_ts_ms = latest_high
    if low_ts_ms == high_ts_ms or high <= low:
        return None
    return DealingRange(
        low=low,
        high=high,
        midpoint=(low + high) / 2.0,
        swing_low_ts_ms=low_ts_ms,
        swing_high_ts_ms=high_ts_ms,
    )


def _duration_ms(tf: str) -> int:
    try:
        return TF_DURATION_MS[tf]
    except KeyError as exc:
        raise ValueError(f"unsupported enrichment timeframe: {tf}") from exc


def _normalized_candle(index: int, candle: Mapping[str, Any], *, tf: str) -> dict[str, Any]:
    return {
        "ts_ms": int(candle["ts_ms"]),
        "tf": tf,
        "open": _finite_float(candle.get("open"), field_name=f"candles[{index}].open"),
        "high": _finite_float(candle.get("high"), field_name=f"candles[{index}].high"),
        "low": _finite_float(candle.get("low"), field_name=f"candles[{index}].low"),
        "close": _finite_float(candle.get("close"), field_name=f"candles[{index}].close"),
        "volume": _finite_float(candle.get("volume", 0), field_name=f"candles[{index}].volume"),
    }


def _finite_float(raw_value: Any, *, field_name: str) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value
