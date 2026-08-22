"""Pure Ichimoku regime classification with dwell and hysteresis."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import replace
from typing import Any, Mapping, Sequence

from runtime.regime.features import RegimeFeatureSeries, build_feature_series, features_at
from runtime.regime.types import RegimeParams, RegimeSnapshot, RegimeState


DEFAULT_PARAMS = RegimeParams()


def classify_bar(
    candles: Sequence[Mapping[str, Any]],
    *,
    index: int | None = None,
    params: RegimeParams = DEFAULT_PARAMS,
    tf: str | None = None,
    htf_candles: Sequence[Mapping[str, Any]] | None = None,
) -> RegimeSnapshot:
    """Classify one closed bar without prior dwell state."""

    if not candles:
        return _snapshot(
            RegimeState.TRANSITION,
            confidence=0.0,
            reasons=("no_candles",),
            features={},
            as_of=None,
            tf=tf or params.regime_tf,
        )
    resolved_index = len(candles) - 1 if index is None else index
    series = build_feature_series(candles, params=params)
    htf_context = (
        _htf_context(htf_candles, params=params)
        if htf_candles is not None and params.use_htf_veto
        else None
    )
    return _candidate_snapshot(
        series,
        index=resolved_index,
        params=params,
        tf=tf or params.regime_tf,
        htf_context=htf_context,
    )


def classify_series(
    candles: Sequence[Mapping[str, Any]],
    *,
    params: RegimeParams = DEFAULT_PARAMS,
    tf: str | None = None,
    htf_candles: Sequence[Mapping[str, Any]] | None = None,
) -> list[RegimeSnapshot]:
    """Classify a candle series and apply closed-bar dwell/hysteresis."""

    if not candles:
        return []

    resolved_tf = tf or params.regime_tf
    feature_series = build_feature_series(candles, params=params)
    htf_context = (
        _htf_context(htf_candles, params=params)
        if htf_candles is not None and params.use_htf_veto
        else None
    )
    snapshots: list[RegimeSnapshot] = []
    current_state: RegimeState | None = None
    pending_state: RegimeState | None = None
    pending_count = 0

    for index in range(len(feature_series.candles)):
        candidate = _candidate_snapshot(
            feature_series,
            index=index,
            params=params,
            tf=resolved_tf,
            htf_context=htf_context,
        )
        emitted, current_state, pending_state, pending_count = _apply_dwell(
            candidate,
            current_state=current_state,
            pending_state=pending_state,
            pending_count=pending_count,
            params=params,
        )
        snapshots.append(emitted)

    return snapshots


def _candidate_snapshot(
    series: RegimeFeatureSeries,
    *,
    index: int,
    params: RegimeParams,
    tf: str,
    htf_context: tuple[tuple[int, ...], list[RegimeSnapshot]] | None,
) -> RegimeSnapshot:
    if index < 0 or index >= len(series.candles):
        raise IndexError("regime index out of range")

    features = features_at(series, index=index, params=params)
    reasons: list[str] = []
    htf_snapshot = _aligned_htf_snapshot(series.candles[index].get("ts_ms"), htf_context)
    htf_disagree = _htf_disagrees(features, htf_snapshot)
    if htf_snapshot is not None:
        features["htf"] = {
            "state": htf_snapshot.state.value,
            "as_of": htf_snapshot.as_of,
            "price_vs_kumo": htf_snapshot.features.get("price_vs_kumo"),
        }
        features["htf_ltf_disagree"] = htf_disagree
    else:
        features["htf_ltf_disagree"] = False
        if not params.use_htf_veto:
            features["htf_veto_disabled"] = True

    if _missing_required(features, params=params):
        return _snapshot(
            RegimeState.TRANSITION,
            confidence=0.0,
            reasons=("missing_required_features",),
            features=features,
            as_of=features.get("ts_ms"),
            tf=tf,
        )

    bull_stack = _trend_stack(features, params=params, direction="bull")
    bear_stack = _trend_stack(features, params=params, direction="bear")
    if bull_stack and not _htf_veto(features, direction="bull"):
        return _snapshot(
            RegimeState.TREND_BULL,
            confidence=0.9,
            reasons=("full_bull_stack",),
            features=features,
            as_of=features.get("ts_ms"),
            tf=tf,
        )
    if bear_stack and not _htf_veto(features, direction="bear"):
        return _snapshot(
            RegimeState.TREND_BEAR,
            confidence=0.9,
            reasons=("full_bear_stack",),
            features=features,
            as_of=features.get("ts_ms"),
            tf=tf,
        )

    if features["future_twist"]:
        reasons.append("future_kumo_twist")
    if htf_disagree:
        reasons.append("htf_ltf_disagree")
    if reasons:
        return _snapshot(
            RegimeState.TRANSITION,
            confidence=0.45,
            reasons=tuple(reasons),
            features=features,
            as_of=features.get("ts_ms"),
            tf=tf,
        )

    if _range_condition(features, params=params):
        return _snapshot(
            RegimeState.RANGE,
            confidence=0.65,
            reasons=("range_condition",),
            features=features,
            as_of=features.get("ts_ms"),
            tf=tf,
        )

    location = features["price_vs_kumo"]
    outside = location in ("above", "below")
    if outside and _outside_weak_or_conflicted(features, params=params):
        return _snapshot(
            RegimeState.VOLATILE,
            confidence=0.6,
            reasons=("outside_kumo_without_trend_agreement",),
            features=features,
            as_of=features.get("ts_ms"),
            tf=tf,
        )

    return _snapshot(
        RegimeState.TRANSITION,
        confidence=0.35,
        reasons=("fail_closed_no_precedence_match",),
        features=features,
        as_of=features.get("ts_ms"),
        tf=tf,
    )


def _apply_dwell(
    candidate: RegimeSnapshot,
    *,
    current_state: RegimeState | None,
    pending_state: RegimeState | None,
    pending_count: int,
    params: RegimeParams,
) -> tuple[RegimeSnapshot, RegimeState, RegimeState | None, int]:
    if not params.use_dwell or params.dwell_bars <= 1:
        return candidate, candidate.state, None, 0

    if current_state is None:
        if pending_state == candidate.state:
            pending_count += 1
        else:
            pending_state = candidate.state
            pending_count = 1
        if pending_count >= params.dwell_bars:
            return candidate, candidate.state, None, 0
        if candidate.state in (RegimeState.TREND_BULL, RegimeState.TREND_BEAR):
            return _with_dwell(candidate, RegimeState.TRANSITION, pending_count), RegimeState.TRANSITION, pending_state, pending_count
        return candidate, candidate.state, pending_state, pending_count

    if candidate.state == current_state:
        return candidate, current_state, None, 0

    if pending_state == candidate.state:
        pending_count += 1
    else:
        pending_state = candidate.state
        pending_count = 1

    if pending_count >= params.dwell_bars:
        return candidate, candidate.state, None, 0

    if candidate.state in (RegimeState.TREND_BULL, RegimeState.TREND_BEAR):
        return _with_dwell(candidate, RegimeState.TRANSITION, pending_count), current_state, pending_state, pending_count
    return _with_dwell(candidate, current_state, pending_count), current_state, pending_state, pending_count


def _with_dwell(
    candidate: RegimeSnapshot,
    state: RegimeState,
    pending_count: int,
) -> RegimeSnapshot:
    features = dict(candidate.features)
    features["dwell_pending_state"] = candidate.state.value
    features["dwell_pending_bars"] = pending_count
    reasons = (*candidate.reasons, f"dwell_pending:{candidate.state.value}:{pending_count}")
    confidence = min(candidate.confidence, 0.5)
    return replace(candidate, state=state, confidence=confidence, reasons=reasons, features=features)


def _trend_stack(
    features: Mapping[str, Any],
    *,
    params: RegimeParams,
    direction: str,
) -> bool:
    if params.use_adx_di:
        adx = features["adx"]
        if adx is None or adx < params.adx_strong:
            return False
    if params.use_kumo_width_atr:
        width = features["kumo_width_atr"]
        if width is None or width < params.thin_kumo_atr:
            return False
    if features["flat_spanb_bars"] >= params.flat_n:
        return False
    if direction == "bull":
        di_agrees = True if not params.use_adx_di else bool(features["di_bullish"])
        return (
            features["price_vs_kumo"] == "above"
            and features["tk_align"] == "bullish"
            and features["chikou_proxy"] == "bullish"
            and di_agrees
        )
    di_agrees = True if not params.use_adx_di else bool(features["di_bearish"])
    return (
        features["price_vs_kumo"] == "below"
        and features["tk_align"] == "bearish"
        and features["chikou_proxy"] == "bearish"
        and di_agrees
    )


def _outside_weak_or_conflicted(features: Mapping[str, Any], *, params: RegimeParams) -> bool:
    location = features["price_vs_kumo"]
    tk = features["tk_align"]
    adx_is_weak = (
        params.use_adx_di
        and (features["adx"] is None or features["adx"] < params.adx_strong)
    )
    di_conflicts = (
        params.use_adx_di
        and (
            (location == "above" and not features["di_bullish"])
            or (location == "below" and not features["di_bearish"])
        )
    )
    tk_conflicts = (
        (location == "above" and tk != "bullish")
        or (location == "below" and tk != "bearish")
    )
    return adx_is_weak or tk_conflicts or di_conflicts


def _range_condition(features: Mapping[str, Any], *, params: RegimeParams) -> bool:
    thin_and_weak = (
        params.use_kumo_width_atr
        and params.use_adx_di
        and features["kumo_width_atr"] is not None
        and features["kumo_width_atr"] < params.thin_kumo_atr
        and features["adx"] is not None
        and features["adx"] < params.adx_weak
    )
    both_tk_flat = features["flat_tenkan_bars"] >= params.flat_n and features["flat_kijun_bars"] >= params.flat_n
    return features["price_vs_kumo"] == "inside" or thin_and_weak or both_tk_flat


def _missing_required(features: Mapping[str, Any], *, params: RegimeParams) -> bool:
    required = [
        "price_vs_kumo",
        "tk_align",
        "chikou_proxy",
    ]
    if params.use_adx_di:
        required.extend(("adx", "plus_di", "minus_di"))
    if params.use_kumo_width_atr:
        required.append("kumo_width_atr")
    for key in required:
        if features.get(key) in (None, "missing"):
            return True
    return False


def _htf_context(
    htf_candles: Sequence[Mapping[str, Any]],
    *,
    params: RegimeParams,
) -> tuple[tuple[int, ...], list[RegimeSnapshot]]:
    htf_params = replace(params, dwell_bars=1, htf_tf=None)
    htf_tf = params.htf_tf or "1d"
    htf_snapshots = classify_series(htf_candles, params=htf_params, tf=htf_tf, htf_candles=None)
    ts_values = tuple(
        int(candle["ts_ms"])
        for candle in build_feature_series(htf_candles, params=htf_params).candles
        if candle.get("ts_ms") is not None
    )
    return ts_values, htf_snapshots


def _aligned_htf_snapshot(
    ts_ms: Any,
    htf_context: tuple[tuple[int, ...], list[RegimeSnapshot]] | None,
) -> RegimeSnapshot | None:
    if htf_context is None or ts_ms is None:
        return None
    ts_values, snapshots = htf_context
    position = bisect_right(ts_values, int(ts_ms)) - 1
    if position < 0 or position >= len(snapshots):
        return None
    return snapshots[position]


def _htf_disagrees(
    features: Mapping[str, Any],
    htf_snapshot: RegimeSnapshot | None,
) -> bool:
    if htf_snapshot is None:
        return False
    ltf_location = features["price_vs_kumo"]
    htf_location = htf_snapshot.features.get("price_vs_kumo")
    return (ltf_location == "above" and htf_location == "below") or (
        ltf_location == "below" and htf_location == "above"
    )


def _htf_veto(features: Mapping[str, Any], *, direction: str) -> bool:
    htf = features.get("htf")
    if not isinstance(htf, Mapping):
        return False
    htf_location = htf.get("price_vs_kumo")
    if direction == "bull":
        return htf_location == "below"
    return htf_location == "above"


def _snapshot(
    state: RegimeState,
    *,
    confidence: float,
    reasons: tuple[str, ...],
    features: Mapping[str, Any],
    as_of: int | None,
    tf: str,
) -> RegimeSnapshot:
    return RegimeSnapshot(
        state=state,
        confidence=confidence,
        reasons=reasons,
        features=dict(features),
        as_of=as_of,
        tf=tf,
    )
