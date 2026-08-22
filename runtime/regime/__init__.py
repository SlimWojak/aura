"""Aura Phase 1 regime permissioning spine."""

from runtime.regime.classify import DEFAULT_PARAMS, classify_bar, classify_series
from runtime.regime.features import (
    build_feature_series,
    chikou_proxy,
    compute_atr,
    compute_directional_movement,
    flat_run_bars,
    future_twist,
    kumo_width_atr,
    price_vs_kumo,
    tk_align,
)
from runtime.regime.gate import regime_allows
from runtime.regime.resample import resample_1h_candles
from runtime.regime.types import (
    REGIME_LABEL_SCHEMA,
    REGIME_SUMMARY_SCHEMA,
    RegimeParams,
    RegimeSnapshot,
    RegimeState,
)

__all__ = [
    "DEFAULT_PARAMS",
    "REGIME_LABEL_SCHEMA",
    "REGIME_SUMMARY_SCHEMA",
    "RegimeParams",
    "RegimeSnapshot",
    "RegimeState",
    "build_feature_series",
    "chikou_proxy",
    "classify_bar",
    "classify_series",
    "compute_atr",
    "compute_directional_movement",
    "flat_run_bars",
    "future_twist",
    "kumo_width_atr",
    "price_vs_kumo",
    "regime_allows",
    "resample_1h_candles",
    "tk_align",
]
