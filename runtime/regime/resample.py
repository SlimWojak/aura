"""OHLCV resampling helpers for the regime labeler."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Any, Mapping, Sequence

from runtime.market.ohlcv import CANDLE_SCHEMA, SOURCE
from runtime.market.symbols import validate_symbol, validate_tf


HOUR_MS = 3_600_000
_TARGET_HOURS = {"1h": 1, "4h": 4, "1d": 24}


def resample_1h_candles(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    target_tf: str,
) -> list[dict[str, Any]]:
    """Aggregate contiguous stored 1h candles into complete target OHLCV bars."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(target_tf)
    if safe_tf not in _TARGET_HOURS:
        raise ValueError("regime resampling supports 1h, 4h, and 1d")

    normalized = sorted(
        [_normalized_1h_candle(index, candle, symbol=safe_symbol) for index, candle in enumerate(candles)],
        key=lambda candle: int(candle["ts_ms"]),
    )
    if safe_tf == "1h":
        return [_retag_candle(candle, tf="1h") for candle in normalized]
    if not normalized:
        return []

    _ensure_contiguous_hourly(normalized)
    bucket_ms = _TARGET_HOURS[safe_tf] * HOUR_MS
    buckets: dict[int, list[dict[str, Any]]] = {}
    for candle in normalized:
        ts_ms = int(candle["ts_ms"])
        bucket_start = (ts_ms // bucket_ms) * bucket_ms
        buckets.setdefault(bucket_start, []).append(candle)

    expected = _TARGET_HOURS[safe_tf]
    resampled: list[dict[str, Any]] = []
    for bucket_start in sorted(buckets):
        rows = buckets[bucket_start]
        if len(rows) != expected:
            continue
        expected_ts = [bucket_start + (offset * HOUR_MS) for offset in range(expected)]
        actual_ts = [int(row["ts_ms"]) for row in rows]
        if actual_ts != expected_ts:
            raise ValueError(f"gap inside {safe_tf} bucket starting {bucket_start}")
        resampled.append(_aggregate_bucket(rows, symbol=safe_symbol, tf=safe_tf, ts_ms=bucket_start))
    return resampled


def _aggregate_bucket(
    rows: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    tf: str,
    ts_ms: int,
) -> dict[str, Any]:
    volume = sum(float(row["volume"]) for row in rows)
    return {
        "schema": CANDLE_SCHEMA,
        "symbol": symbol,
        "tf": tf,
        "ts_ms": ts_ms,
        "source": SOURCE,
        "ingested_at": _latest_ingested_at(rows),
        "open": _format_float(float(rows[0]["open"])),
        "high": _format_float(max(float(row["high"]) for row in rows)),
        "low": _format_float(min(float(row["low"]) for row in rows)),
        "close": _format_float(float(rows[-1]["close"])),
        "volume": _format_float(volume),
    }


def _normalized_1h_candle(
    index: int,
    candle: Mapping[str, Any],
    *,
    symbol: str,
) -> dict[str, Any]:
    if candle.get("schema") != CANDLE_SCHEMA:
        raise ValueError(f"candles[{index}] invalid candle schema")
    if validate_symbol(str(candle.get("symbol", ""))) != symbol:
        raise ValueError(f"candles[{index}] symbol mismatch")
    if validate_tf(str(candle.get("tf", ""))) != "1h":
        raise ValueError(f"candles[{index}] must be stored 1h candle")
    ts_ms = _integer(candle.get("ts_ms"), field_name=f"candles[{index}].ts_ms")
    return {
        "schema": CANDLE_SCHEMA,
        "symbol": symbol,
        "tf": "1h",
        "ts_ms": ts_ms,
        "source": SOURCE,
        "ingested_at": str(candle.get("ingested_at", "")),
        "open": _format_float(_finite_float(candle.get("open"), field_name=f"candles[{index}].open")),
        "high": _format_float(_finite_float(candle.get("high"), field_name=f"candles[{index}].high")),
        "low": _format_float(_finite_float(candle.get("low"), field_name=f"candles[{index}].low")),
        "close": _format_float(_finite_float(candle.get("close"), field_name=f"candles[{index}].close")),
        "volume": _format_float(_finite_float(candle.get("volume"), field_name=f"candles[{index}].volume")),
    }


def _retag_candle(candle: Mapping[str, Any], *, tf: str) -> dict[str, Any]:
    retagged = dict(candle)
    retagged["tf"] = tf
    return retagged


def _ensure_contiguous_hourly(candles: Sequence[Mapping[str, Any]]) -> None:
    for index in range(1, len(candles)):
        previous_ts = int(candles[index - 1]["ts_ms"])
        ts_ms = int(candles[index]["ts_ms"])
        if ts_ms - previous_ts != HOUR_MS:
            raise ValueError(f"gap in stored 1h candles between {previous_ts} and {ts_ms}")


def _latest_ingested_at(rows: Sequence[Mapping[str, Any]]) -> str:
    values = [str(row.get("ingested_at", "")) for row in rows if row.get("ingested_at")]
    if values:
        return max(values)
    return datetime.fromtimestamp(int(rows[-1]["ts_ms"]) / 1000, tz=UTC).isoformat().replace("+00:00", "Z")


def _integer(raw_value: Any, *, field_name: str) -> int:
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _finite_float(raw_value: Any, *, field_name: str) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _format_float(value: float) -> str:
    return format(value, ".10f").rstrip("0").rstrip(".") or "0"
