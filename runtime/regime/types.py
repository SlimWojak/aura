"""Typed records for Aura regime permissioning labels."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


REGIME_LABEL_SCHEMA = "aura.regime_label.v1"
REGIME_SUMMARY_SCHEMA = "aura.regime_summary.v1"


class RegimeState(StrEnum):
    """The only Phase 1 regime permissioning states."""

    TREND_BULL = "TREND_BULL"
    TREND_BEAR = "TREND_BEAR"
    TRANSITION = "TRANSITION"
    RANGE = "RANGE"
    VOLATILE = "VOLATILE"


@dataclass(frozen=True, slots=True)
class RegimeParams:
    """Frozen Phase 1 default constants for the regime spine."""

    tenkan: int = 9
    kijun: int = 26
    senkou_b: int = 52
    displacement: int = 26
    regime_tf: str = "4h"
    htf_tf: str | None = "1d"
    adx_period: int = 14
    adx_weak: float = 20.0
    adx_strong: float = 25.0
    thin_kumo_atr: float = 0.4
    flat_n: int = 8
    flat_atr_fraction: float = 0.05
    dwell_bars: int = 3

    @property
    def minimum_candles(self) -> int:
        ichimoku_ready = self.senkou_b + self.displacement
        adx_ready = (2 * self.adx_period) - 1
        return max(ichimoku_ready, adx_ready, self.flat_n)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenkan": self.tenkan,
            "kijun": self.kijun,
            "senkou_b": self.senkou_b,
            "displacement": self.displacement,
            "regime_tf": self.regime_tf,
            "htf_tf": self.htf_tf,
            "adx_period": self.adx_period,
            "adx_weak": self.adx_weak,
            "adx_strong": self.adx_strong,
            "thin_kumo_atr": self.thin_kumo_atr,
            "flat_n": self.flat_n,
            "flat_atr_fraction": self.flat_atr_fraction,
            "dwell_bars": self.dwell_bars,
            "minimum_candles": self.minimum_candles,
        }


@dataclass(frozen=True, slots=True)
class RegimeSnapshot:
    """One closed-bar regime label and its auditable feature payload."""

    state: RegimeState
    confidence: float
    reasons: tuple[str, ...]
    features: Mapping[str, Any]
    as_of: int | None
    tf: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REGIME_LABEL_SCHEMA,
            "state": self.state.value,
            "confidence": round(self.confidence, 10),
            "reasons": list(self.reasons),
            "features": _stable_mapping(self.features),
            "as_of": self.as_of,
            "tf": self.tf,
        }


def _stable_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    stable: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            stable[key] = _stable_mapping(value)
        elif isinstance(value, float):
            stable[key] = round(value, 10)
        elif isinstance(value, tuple):
            stable[key] = list(value)
        else:
            stable[key] = value
    return stable
