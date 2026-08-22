"""Pure feature math for Aura's Ichimoku regime classifier."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, Mapping, Sequence

from runtime.brain.ichimoku import compute_ichimoku
from runtime.brain.types import IchimokuParams, IchimokuPoint, IchimokuSeries
from runtime.regime.types import RegimeParams


PriceVsKumo = Literal["above", "below", "inside", "missing"]
TkAlign = Literal["bullish", "bearish", "flat", "missing"]
ChikouProxy = Literal["bullish", "bearish", "flat", "missing"]


@dataclass(frozen=True, slots=True)
class DirectionalMovementSeries:
    """Wilder ADX and directional indicators aligned to input candles."""

    atr: tuple[float | None, ...]
    adx: tuple[float | None, ...]
    plus_di: tuple[float | None, ...]
    minus_di: tuple[float | None, ...]


@dataclass(frozen=True, slots=True)
class RegimeFeatureSeries:
    """Precomputed indicator series used by the classifier."""

    candles: tuple[Mapping[str, Any], ...]
    ichimoku: IchimokuSeries
    atr: tuple[float | None, ...]
    adx: tuple[float | None, ...]
    plus_di: tuple[float | None, ...]
    minus_di: tuple[float | None, ...]
    flat_spanb_bars: tuple[int, ...]
    flat_kijun_bars: tuple[int, ...]
    flat_tenkan_bars: tuple[int, ...]


def build_feature_series(
    candles: Sequence[Mapping[str, Any]],
    *,
    params: RegimeParams,
) -> RegimeFeatureSeries:
    """Precompute all regime features without side effects."""

    normalized = tuple(_normalized_candle(index, candle) for index, candle in enumerate(candles))
    ichi_params = IchimokuParams(
        tenkan=params.tenkan,
        kijun=params.kijun,
        senkou_b=params.senkou_b,
        displacement=params.displacement,
    )
    ichimoku = compute_ichimoku(normalized, params=ichi_params)
    directional = compute_directional_movement(normalized, period=params.adx_period)
    span_b = tuple(point.senkou_span_b_displaced for point in ichimoku.points)
    kijun = tuple(point.kijun for point in ichimoku.points)
    tenkan = tuple(point.tenkan for point in ichimoku.points)

    return RegimeFeatureSeries(
        candles=normalized,
        ichimoku=ichimoku,
        atr=directional.atr,
        adx=directional.adx,
        plus_di=directional.plus_di,
        minus_di=directional.minus_di,
        flat_spanb_bars=tuple(
            flat_run_bars(
                span_b,
                directional.atr,
                index=index,
                max_bars=params.flat_n,
                atr_fraction=params.flat_atr_fraction,
            )
            for index in range(len(normalized))
        ),
        flat_kijun_bars=tuple(
            flat_run_bars(
                kijun,
                directional.atr,
                index=index,
                max_bars=params.flat_n,
                atr_fraction=params.flat_atr_fraction,
            )
            for index in range(len(normalized))
        ),
        flat_tenkan_bars=tuple(
            flat_run_bars(
                tenkan,
                directional.atr,
                index=index,
                max_bars=params.flat_n,
                atr_fraction=params.flat_atr_fraction,
            )
            for index in range(len(normalized))
        ),
    )


def features_at(
    series: RegimeFeatureSeries,
    *,
    index: int,
    params: RegimeParams,
) -> dict[str, Any]:
    """Return auditable scalar features for one closed bar."""

    point = series.ichimoku.points[index]
    location = price_vs_kumo(point)
    cloud_top, cloud_bottom = displaced_cloud_bounds(point)
    atr_value = series.atr[index]
    width_atr = kumo_width_atr(point, atr_value)
    tk = tk_align(point)
    chikou = chikou_proxy(series.ichimoku, index=index)
    flat_spanb = series.flat_spanb_bars[index]
    flat_kijun = series.flat_kijun_bars[index]
    flat_tenkan = series.flat_tenkan_bars[index]
    adx_value = series.adx[index]
    plus_di_value = series.plus_di[index]
    minus_di_value = series.minus_di[index]

    return {
        "index": index,
        "ts_ms": point.ts_ms,
        "close": point.close,
        "tenkan": point.tenkan,
        "kijun": point.kijun,
        "senkou_span_a_raw": point.senkou_span_a_raw,
        "senkou_span_b_raw": point.senkou_span_b_raw,
        "senkou_span_a_displaced": point.senkou_span_a_displaced,
        "senkou_span_b_displaced": point.senkou_span_b_displaced,
        "cloud_top": cloud_top,
        "cloud_bottom": cloud_bottom,
        "price_vs_kumo": location,
        "tk_align": tk,
        "chikou_proxy": chikou,
        "atr": atr_value,
        "adx": adx_value,
        "plus_di": plus_di_value,
        "minus_di": minus_di_value,
        "di_bullish": _greater(plus_di_value, minus_di_value),
        "di_bearish": _greater(minus_di_value, plus_di_value),
        "kumo_width_atr": width_atr,
        "thin_kumo": width_atr is not None and width_atr < params.thin_kumo_atr,
        "flat_spanb_bars": flat_spanb,
        "flat_kijun_bars": flat_kijun,
        "flat_tenkan_bars": flat_tenkan,
        "flat_spanb": flat_spanb >= params.flat_n,
        "flat_kijun": flat_kijun >= params.flat_n,
        "flat_tenkan": flat_tenkan >= params.flat_n,
        "future_twist": future_twist(point),
    }


def compute_atr(
    candles: Sequence[Mapping[str, Any]],
    *,
    period: int,
) -> list[float | None]:
    """Compute Wilder ATR values aligned to input candles."""

    return list(compute_directional_movement(candles, period=period).atr)


def compute_directional_movement(
    candles: Sequence[Mapping[str, Any]],
    *,
    period: int,
) -> DirectionalMovementSeries:
    """Compute ATR, ADX, +DI, and -DI with Wilder smoothing."""

    if period <= 0:
        raise ValueError("ADX period must be positive")

    rows = [_normalized_candle(index, candle) for index, candle in enumerate(candles)]
    count = len(rows)
    atr: list[float | None] = [None] * count
    adx: list[float | None] = [None] * count
    plus_di: list[float | None] = [None] * count
    minus_di: list[float | None] = [None] * count
    if count < period:
        return DirectionalMovementSeries(tuple(atr), tuple(adx), tuple(plus_di), tuple(minus_di))

    true_ranges = [0.0] * count
    plus_dm = [0.0] * count
    minus_dm = [0.0] * count
    for index, row in enumerate(rows):
        if index == 0:
            true_ranges[index] = row["high"] - row["low"]
            continue
        previous = rows[index - 1]
        true_ranges[index] = max(
            row["high"] - row["low"],
            abs(row["high"] - previous["close"]),
            abs(row["low"] - previous["close"]),
        )
        up_move = row["high"] - previous["high"]
        down_move = previous["low"] - row["low"]
        plus_dm[index] = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm[index] = down_move if down_move > up_move and down_move > 0 else 0.0

    smoothed_tr = sum(true_ranges[1 : period + 1])
    smoothed_plus_dm = sum(plus_dm[1 : period + 1])
    smoothed_minus_dm = sum(minus_dm[1 : period + 1])
    dx: list[float | None] = [None] * count
    if period < count:
        _store_directional(
            index=period,
            smoothed_tr=smoothed_tr,
            smoothed_plus_dm=smoothed_plus_dm,
            smoothed_minus_dm=smoothed_minus_dm,
            atr_values=atr,
            plus_di_values=plus_di,
            minus_di_values=minus_di,
            dx_values=dx,
            period=period,
        )

    for index in range(period + 1, count):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + true_ranges[index]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm[index]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm[index]
        _store_directional(
            index=index,
            smoothed_tr=smoothed_tr,
            smoothed_plus_dm=smoothed_plus_dm,
            smoothed_minus_dm=smoothed_minus_dm,
            atr_values=atr,
            plus_di_values=plus_di,
            minus_di_values=minus_di,
            dx_values=dx,
            period=period,
        )

    first_adx_index = (2 * period) - 1
    if first_adx_index < count:
        first_dx_values = [value for value in dx[period : first_adx_index + 1] if value is not None]
        if len(first_dx_values) == period:
            previous_adx = sum(first_dx_values) / period
            adx[first_adx_index] = previous_adx
            for index in range(first_adx_index + 1, count):
                dx_value = dx[index]
                if dx_value is None:
                    continue
                previous_adx = ((previous_adx * (period - 1)) + dx_value) / period
                adx[index] = previous_adx

    return DirectionalMovementSeries(tuple(atr), tuple(adx), tuple(plus_di), tuple(minus_di))


def flat_run_bars(
    values: Sequence[float | None],
    atr_values: Sequence[float | None],
    *,
    index: int,
    max_bars: int,
    atr_fraction: float,
) -> int:
    """Return the largest lookback run whose net change is tiny versus ATR."""

    if max_bars <= 1 or index < 0 or index >= len(values):
        return 0
    current = values[index]
    atr_value = atr_values[index] if index < len(atr_values) else None
    if current is None or atr_value is None or atr_value <= 0:
        return 0
    threshold = atr_value * atr_fraction
    largest = 1
    start = max(0, index - max_bars + 1)
    for left in range(index - 1, start - 1, -1):
        previous = values[left]
        if previous is None:
            break
        if abs(current - previous) <= threshold:
            largest = index - left + 1
    return largest


def price_vs_kumo(point: IchimokuPoint) -> PriceVsKumo:
    """Classify close against the displaced cloud under the current bar."""

    cloud_top, cloud_bottom = displaced_cloud_bounds(point)
    if cloud_top is None or cloud_bottom is None:
        return "missing"
    if point.close > cloud_top:
        return "above"
    if point.close < cloud_bottom:
        return "below"
    return "inside"


def displaced_cloud_bounds(point: IchimokuPoint) -> tuple[float | None, float | None]:
    span_a = point.senkou_span_a_displaced
    span_b = point.senkou_span_b_displaced
    if span_a is None or span_b is None:
        return None, None
    return max(span_a, span_b), min(span_a, span_b)


def tk_align(point: IchimokuPoint) -> TkAlign:
    if point.tenkan is None or point.kijun is None:
        return "missing"
    if point.tenkan > point.kijun:
        return "bullish"
    if point.tenkan < point.kijun:
        return "bearish"
    return "flat"


def chikou_proxy(series: IchimokuSeries, *, index: int) -> ChikouProxy:
    point = series.points[index]
    reference_index = index - series.params.displacement
    if reference_index < 0:
        return "missing"
    reference_close = series.points[reference_index].close
    if point.close > reference_close:
        return "bullish"
    if point.close < reference_close:
        return "bearish"
    return "flat"


def kumo_width_atr(point: IchimokuPoint, atr_value: float | None) -> float | None:
    if (
        point.senkou_span_a_displaced is None
        or point.senkou_span_b_displaced is None
        or atr_value is None
        or atr_value <= 0
    ):
        return None
    return abs(point.senkou_span_a_displaced - point.senkou_span_b_displaced) / atr_value


def future_twist(point: IchimokuPoint) -> bool:
    """Detect a known future cloud twist from raw versus displaced span polarity."""

    if (
        point.senkou_span_a_raw is None
        or point.senkou_span_b_raw is None
        or point.senkou_span_a_displaced is None
        or point.senkou_span_b_displaced is None
    ):
        return False
    current_sign = _sign(point.senkou_span_a_displaced - point.senkou_span_b_displaced)
    future_sign = _sign(point.senkou_span_a_raw - point.senkou_span_b_raw)
    return current_sign != 0 and future_sign != 0 and current_sign != future_sign


def _store_directional(
    *,
    index: int,
    smoothed_tr: float,
    smoothed_plus_dm: float,
    smoothed_minus_dm: float,
    atr_values: list[float | None],
    plus_di_values: list[float | None],
    minus_di_values: list[float | None],
    dx_values: list[float | None],
    period: int,
) -> None:
    atr_values[index] = smoothed_tr / period
    if smoothed_tr <= 0:
        plus_di_values[index] = 0.0
        minus_di_values[index] = 0.0
        dx_values[index] = 0.0
        return
    plus_di = 100.0 * (smoothed_plus_dm / smoothed_tr)
    minus_di = 100.0 * (smoothed_minus_dm / smoothed_tr)
    plus_di_values[index] = plus_di
    minus_di_values[index] = minus_di
    denominator = plus_di + minus_di
    dx_values[index] = 0.0 if denominator == 0 else 100.0 * abs(plus_di - minus_di) / denominator


def _normalized_candle(index: int, candle: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": candle.get("schema"),
        "symbol": candle.get("symbol"),
        "tf": candle.get("tf"),
        "ts_ms": _optional_int(candle.get("ts_ms")),
        "source": candle.get("source"),
        "ingested_at": candle.get("ingested_at"),
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


def _optional_int(raw_value: Any) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("candle ts_ms must be an integer when present") from exc


def _greater(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
