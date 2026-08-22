"""Typed records for deterministic Aura brain signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


BRAIN_SIGNAL_SCHEMA = "aura.brain_signal.v1"
ICHIMOKU_SIGNAL_SCHEMA = "aura.ichimoku_signal.v1"
Bias = Literal["long", "short", "flat"]


@dataclass(frozen=True, slots=True)
class IchimokuParams:
    """Standard Ichimoku constants used by Aura v0."""

    tenkan: int = 9
    kijun: int = 26
    senkou_b: int = 52
    displacement: int = 26

    @property
    def minimum_candles(self) -> int:
        return self.senkou_b + self.displacement

    def to_dict(self) -> dict[str, int]:
        return {
            "tenkan": self.tenkan,
            "kijun": self.kijun,
            "senkou_b": self.senkou_b,
            "displacement": self.displacement,
            "minimum_candles": self.minimum_candles,
        }


@dataclass(frozen=True, slots=True)
class IchimokuPoint:
    """One candle row with raw and chart-displaced Ichimoku components."""

    index: int
    ts_ms: int | None
    high: float
    low: float
    close: float
    tenkan: float | None
    kijun: float | None
    senkou_span_a_raw: float | None
    senkou_span_b_raw: float | None
    senkou_span_a_displaced: float | None
    senkou_span_b_displaced: float | None
    chikou_span_displaced_back: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "ts_ms": self.ts_ms,
            "high": _stable_float(self.high),
            "low": _stable_float(self.low),
            "close": _stable_float(self.close),
            "tenkan": _stable_float(self.tenkan),
            "kijun": _stable_float(self.kijun),
            "senkou_span_a_raw": _stable_float(self.senkou_span_a_raw),
            "senkou_span_b_raw": _stable_float(self.senkou_span_b_raw),
            "senkou_span_a_displaced": _stable_float(self.senkou_span_a_displaced),
            "senkou_span_b_displaced": _stable_float(self.senkou_span_b_displaced),
            "chikou_span_displaced_back": _stable_float(self.chikou_span_displaced_back),
        }


@dataclass(frozen=True, slots=True)
class IchimokuSeries:
    """Ichimoku rows for a candle sequence."""

    ok: bool
    reason: str | None
    params: IchimokuParams
    points: tuple[IchimokuPoint, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "params": self.params.to_dict(),
            "points": [point.to_dict() for point in self.points],
        }


@dataclass(frozen=True, slots=True)
class IchimokuSignal:
    """Latest closed-bar v0 Ichimoku bias and retunable feature flags."""

    ok: bool
    reason: str | None
    bias: Bias
    index: int | None
    ts_ms: int | None
    params: IchimokuParams
    components: Mapping[str, Any]
    features: Mapping[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ICHIMOKU_SIGNAL_SCHEMA,
            "ok": self.ok,
            "reason": self.reason,
            "bias": self.bias,
            "index": self.index,
            "ts_ms": self.ts_ms,
            "params": self.params.to_dict(),
            "components": _stable_mapping(self.components),
            "features": dict(self.features),
        }


def _stable_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _stable_float(value) for key, value in values.items()}


def _stable_float(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 10)
    return value
