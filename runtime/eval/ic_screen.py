"""Per-bar Ichimoku/regime feature screen for forward ATR returns."""

from __future__ import annotations

from csv import DictWriter
from datetime import UTC, datetime
import json
from math import isfinite, sqrt
from pathlib import Path
from typing import Any, Mapping, Sequence

from runtime.eval.statistics import DEFAULT_ATR_PERIOD, compute_wilder_atr, normal_cdf
from runtime.market.ohlcv import ohlcv_path, read_candles
from runtime.market.symbols import validate_symbol, validate_tf
from runtime.regime.classify import classify_series
from runtime.regime.enrichment import (
    align_daily_dealing_ranges,
    align_latest_fvg,
    chikou_clears_dealing_range,
    chikou_dealing_range_clearance_atr,
    dealing_range_position,
    dealing_range_side,
    flat_spanb_overlaps_fvg,
    fvg_distance_atr,
)
from runtime.regime.features import build_feature_series, displaced_cloud_bounds, features_at
from runtime.regime.types import RegimeParams, RegimeState


IC_SCREEN_SCHEMA = "aura.ic_feature_screen.v1"
DEFAULT_SCREEN_SYMBOLS = ("PF_XBTUSD", "PF_ETHUSD")
DEFAULT_SCREEN_HORIZONS = (4, 12, 24, 48)
DEFAULT_MIN_COUNT = 20
CI_Z = 1.959963984540054
BH_ALPHA = 0.05
CI_METHOD = "newey_west_hac_bartlett"

ICHIMOKU_CONTINUOUS_FEATURES = (
    "price_cloud_distance_atr",
    "tk_spread_atr",
    "chikou_gap_atr",
    "kumo_width_atr",
    "adx",
    "di_spread",
    "flat_spanb_bars",
    "flat_kijun_bars",
    "flat_tenkan_bars",
)

ICHIMOKU_CATEGORICAL_LEVELS: dict[str, tuple[Any, ...] | None] = {
    "regime_state": tuple(state.value for state in RegimeState),
    "cloud_bias": (-1, 0, 1),
    "price_vs_kumo": ("above", "below", "inside"),
    "tk_align": ("bullish", "bearish", "flat"),
    "chikou_proxy": ("bullish", "bearish", "flat"),
    "thin_kumo": (False, True),
    "future_twist": (False, True),
}

ENRICHMENT_CONTINUOUS_FEATURES = (
    "daily_dr_position",
    "daily_fvg_distance_atr",
    "chikou_daily_dr_clearance_atr",
)

ENRICHMENT_CATEGORICAL_LEVELS: dict[str, tuple[Any, ...] | None] = {
    "daily_dr_side": ("discount", "equilibrium", "premium"),
    "daily_fvg_side": ("bullish", "bearish", "none"),
    "daily_fvg_price_inside": (False, True),
    "chikou_clears_daily_dr": (False, True),
    "fvg_flat_spanb_overlap": (False, True),
}

CONTINUOUS_FEATURES = ICHIMOKU_CONTINUOUS_FEATURES
CATEGORICAL_LEVELS = ICHIMOKU_CATEGORICAL_LEVELS
FEATURE_SETS = ("ichimoku", "enrichment", "all")


def run_ic_screen_from_store(
    *,
    symbols: Sequence[str] = DEFAULT_SCREEN_SYMBOLS,
    tf: str = "1h",
    aura_root: str | Path | None = None,
    horizons: Sequence[int] = DEFAULT_SCREEN_HORIZONS,
    atr_period: int = DEFAULT_ATR_PERIOD,
    min_count: int = DEFAULT_MIN_COUNT,
    max_bars: int | None = None,
    since_ts_ms: int | None = None,
    feature_set: str = "ichimoku",
) -> dict[str, Any]:
    """Load stored OHLCV and run the paper-only bar feature screen."""

    safe_symbols = tuple(validate_symbol(symbol) for symbol in symbols)
    safe_tf = validate_tf(tf)
    candles_by_symbol = {
        symbol: _window_candles(
            read_candles(symbol, safe_tf, aura_root_override=aura_root),
            max_bars=max_bars,
            since_ts_ms=since_ts_ms,
        )
        for symbol in safe_symbols
    }
    return run_ic_screen(
        candles_by_symbol,
        tf=safe_tf,
        horizons=horizons,
        atr_period=atr_period,
        min_count=min_count,
        aura_root=aura_root,
        feature_set=feature_set,
    )


def run_ic_screen(
    candles_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    tf: str,
    horizons: Sequence[int] = DEFAULT_SCREEN_HORIZONS,
    atr_period: int = DEFAULT_ATR_PERIOD,
    min_count: int = DEFAULT_MIN_COUNT,
    aura_root: str | Path | None = None,
    feature_set: str = "ichimoku",
) -> dict[str, Any]:
    """Score closed-bar feature values against forward ATR-normalized returns."""

    safe_tf = validate_tf(tf)
    safe_horizons = _validated_horizons(horizons)
    safe_feature_set = _validated_feature_set(feature_set)
    if atr_period <= 0:
        raise ValueError("atr_period must be positive")
    if min_count <= 0:
        raise ValueError("min_count must be positive")

    symbol_reports = []
    scores: list[dict[str, Any]] = []
    for symbol, candles in candles_by_symbol.items():
        safe_symbol = validate_symbol(symbol)
        symbol_report = score_symbol(
            candles,
            symbol=safe_symbol,
            tf=safe_tf,
            horizons=safe_horizons,
            atr_period=atr_period,
            min_count=min_count,
            feature_set=safe_feature_set,
        )
        symbol_reports.append(symbol_report)
        scores.extend(symbol_report["scores"])

    _apply_benjamini_hochberg(scores)
    kill_summary = summarize_kill_rule(scores, symbols=[report["symbol"] for report in symbol_reports])
    generated_at = utc_now_iso()
    return {
        "schema": IC_SCREEN_SCHEMA,
        "ok": True,
        "generated_at": generated_at,
        "symbols": [report["symbol"] for report in symbol_reports],
        "tf": safe_tf,
        "feature_set": safe_feature_set,
        "horizons": list(safe_horizons),
        "atr_period": atr_period,
        "min_count": min_count,
        "aura_root": None if aura_root is None else str(aura_root),
        "market_paths": {
            report["symbol"]: str(ohlcv_path(report["symbol"], safe_tf, aura_root_override=aura_root))
            for report in symbol_reports
        },
        "feature_contract": _feature_contract(safe_feature_set),
        "lookahead_note": (
            "Bar t features use closed-bar values only. Cloud features read "
            "Ichimoku displaced spans under bar t, which are raw spans from "
            "t-displacement. Chikou gap uses close[t] - close[t-displacement]; "
            "the chart-displaced future Chikou value is not used. Enrichment "
            "features use only completed higher-timeframe candles; Daily DR "
            "swings require the next daily candle to close before confirmation, "
            "and Chikou-vs-DR compares close[t] with the Daily DR known at "
            "t-displacement."
        ),
        "forward_return_note": (
            "Forward returns are (close[t+horizon] - close[t]) / ATR[t], "
            "using Wilder ATR aligned to the decision bar."
        ),
        "ci_note": (
            "CIs and p-values use Newey-West HAC standard errors with Bartlett "
            "weights and lag=min(horizon, n-1) to account for overlapping "
            "forward returns."
        ),
        "multiple_testing_note": (
            "Benjamini-Hochberg q-values are computed across every emitted "
            "symbol x feature/level x horizon test."
        ),
        "kill_rule_note": (
            "A feature is reported dead when every usable CI for both required "
            "symbols spans 0. Survivors are feature-screen candidates only, not "
            "Track A keeps or cartridge promotions."
        ),
        "symbols_detail": symbol_reports,
        "scores": scores,
        "kill_summary": kill_summary,
    }


def score_symbol(
    candles: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    tf: str,
    horizons: Sequence[int],
    atr_period: int = DEFAULT_ATR_PERIOD,
    min_count: int = DEFAULT_MIN_COUNT,
    params: RegimeParams | None = None,
    feature_set: str = "ichimoku",
) -> dict[str, Any]:
    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    if not candles:
        raise ValueError(f"no stored candles for {safe_symbol} {safe_tf}")
    safe_feature_set = _validated_feature_set(feature_set)
    resolved_params = params or RegimeParams(regime_tf=safe_tf, htf_tf=None)
    feature_rows = build_bar_feature_rows(
        candles,
        tf=safe_tf,
        params=resolved_params,
        atr_period=atr_period,
        symbol=safe_symbol,
        feature_set=safe_feature_set,
    )
    closes = [_finite_float(candle.get("close"), f"candles[{index}].close") for index, candle in enumerate(candles)]
    atr_values = compute_wilder_atr(candles, period=atr_period)
    scores: list[dict[str, Any]] = []
    for horizon in horizons:
        returns = _forward_atr_returns(closes, atr_values, horizon=horizon)
        continuous_features, categorical_levels = _features_for_set(safe_feature_set)
        for feature_name in continuous_features:
            scores.append(
                _score_continuous_feature(
                    feature_rows,
                    returns,
                    feature_name=feature_name,
                    symbol=safe_symbol,
                    tf=safe_tf,
                    horizon=horizon,
                    min_count=min_count,
                )
            )
        for feature_name, fixed_levels in categorical_levels.items():
            scores.extend(
                _score_categorical_feature(
                    feature_rows,
                    returns,
                    feature_name=feature_name,
                    fixed_levels=fixed_levels,
                    symbol=safe_symbol,
                    tf=safe_tf,
                    horizon=horizon,
                    min_count=min_count,
                )
            )
    return {
        "symbol": safe_symbol,
        "tf": safe_tf,
        "candle_count": len(candles),
        "feature_row_count": len(feature_rows),
        "first_ts_ms": candles[0].get("ts_ms"),
        "last_ts_ms": candles[-1].get("ts_ms"),
        "scores": scores,
    }


def build_bar_feature_rows(
    candles: Sequence[Mapping[str, Any]],
    *,
    tf: str,
    params: RegimeParams | None = None,
    atr_period: int = DEFAULT_ATR_PERIOD,
    symbol: str | None = None,
    feature_set: str = "ichimoku",
) -> list[dict[str, Any]]:
    """Build look-ahead-safe feature rows aligned to input candles."""

    safe_tf = validate_tf(tf)
    safe_feature_set = _validated_feature_set(feature_set)
    include_enrichment = safe_feature_set in ("enrichment", "all")
    safe_symbol = validate_symbol(symbol) if symbol is not None else None
    if include_enrichment and safe_tf != "1h":
        raise ValueError("enrichment feature set requires stored 1h candles")
    if include_enrichment and safe_symbol is None:
        safe_symbol = _symbol_from_candles(candles)
    resolved_params = params or RegimeParams(regime_tf=safe_tf, htf_tf=None)
    feature_series = build_feature_series(candles, params=resolved_params)
    regime_snapshots = classify_series(candles, params=resolved_params, tf=safe_tf, htf_candles=None)
    atr_values = compute_wilder_atr(candles, period=atr_period)
    closes = [point.close for point in feature_series.ichimoku.points]
    daily_ranges = (
        align_daily_dealing_ranges(candles, symbol=safe_symbol, source_tf=safe_tf)
        if include_enrichment
        else [None] * len(candles)
    )
    daily_fvgs = (
        align_latest_fvg(candles, symbol=safe_symbol, source_tf=safe_tf, target_tf="1d")
        if include_enrichment
        else [None] * len(candles)
    )
    rows: list[dict[str, Any]] = []
    for index in range(len(candles)):
        features = features_at(feature_series, index=index, params=resolved_params)
        point = feature_series.ichimoku.points[index]
        atr = atr_values[index]
        close = point.close
        cloud_top, cloud_bottom = displaced_cloud_bounds(point)
        cloud_bias = _cloud_bias(features.get("price_vs_kumo"))
        row = {
            "index": index,
            "ts_ms": point.ts_ms,
            "regime_state": regime_snapshots[index].state.value,
            "cloud_bias": cloud_bias,
            "price_vs_kumo": _missing_to_none(features.get("price_vs_kumo")),
            "tk_align": _missing_to_none(features.get("tk_align")),
            "chikou_proxy": _missing_to_none(features.get("chikou_proxy")),
            "thin_kumo": features.get("thin_kumo"),
            "future_twist": features.get("future_twist"),
            "price_cloud_distance_atr": _price_cloud_distance_atr(
                close=close,
                cloud_top=cloud_top,
                cloud_bottom=cloud_bottom,
                atr=atr,
            ),
            "tk_spread_atr": _spread_atr(point.tenkan, point.kijun, atr),
            "chikou_gap_atr": _chikou_gap_atr(
                feature_series.ichimoku.points,
                index=index,
                displacement=feature_series.ichimoku.params.displacement,
                atr=atr,
            ),
            "kumo_width_atr": _kumo_width_atr(
                point.senkou_span_a_displaced,
                point.senkou_span_b_displaced,
                atr,
            ),
            "adx": features.get("adx"),
            "di_spread": _spread(features.get("plus_di"), features.get("minus_di")),
            "flat_spanb_bars": features.get("flat_spanb_bars"),
            "flat_kijun_bars": features.get("flat_kijun_bars"),
            "flat_tenkan_bars": features.get("flat_tenkan_bars"),
        }
        if include_enrichment:
            daily_range = daily_ranges[index]
            daily_fvg = daily_fvgs[index]
            row.update(
                {
                    "daily_dr_side": dealing_range_side(close, daily_range),
                    "daily_dr_position": dealing_range_position(close, daily_range),
                    "daily_fvg_side": "none" if daily_fvg is None else daily_fvg.side,
                    "daily_fvg_price_inside": False if daily_fvg is None else daily_fvg.contains(close),
                    "daily_fvg_distance_atr": fvg_distance_atr(close, daily_fvg, atr),
                    "chikou_clears_daily_dr": chikou_clears_dealing_range(
                        closes,
                        daily_ranges,
                        index=index,
                        displacement=feature_series.ichimoku.params.displacement,
                    ),
                    "chikou_daily_dr_clearance_atr": chikou_dealing_range_clearance_atr(
                        closes,
                        daily_ranges,
                        index=index,
                        displacement=feature_series.ichimoku.params.displacement,
                        atr=atr,
                    ),
                    "fvg_flat_spanb_overlap": flat_spanb_overlaps_fvg(
                        span_b=point.senkou_span_b_displaced,
                        flat_spanb_bars=features.get("flat_spanb_bars"),
                        flat_n=resolved_params.flat_n,
                        gap=daily_fvg,
                    ),
                }
            )
        rows.append(row)
    return rows


def summarize_kill_rule(scores: Sequence[Mapping[str, Any]], *, symbols: Sequence[str]) -> list[dict[str, Any]]:
    safe_symbols = tuple(validate_symbol(symbol) for symbol in symbols)
    feature_names = sorted({str(score["feature"]) for score in scores})
    summary = []
    for feature_name in feature_names:
        feature_scores = [score for score in scores if score["feature"] == feature_name]
        by_symbol: dict[str, list[Mapping[str, Any]]] = {
            symbol: [score for score in feature_scores if score["symbol"] == symbol and score.get("enough_data")]
            for symbol in safe_symbols
        }
        symbol_status: dict[str, str] = {}
        best_rows = []
        for symbol, rows in by_symbol.items():
            if not rows:
                symbol_status[symbol] = "insufficient"
                continue
            nonzero_rows = [row for row in rows if not bool(row.get("ci_spans_zero"))]
            symbol_status[symbol] = "nonzero_ci" if nonzero_rows else "all_ci_span_zero"
            best_rows.extend(rows)
        if any(status == "nonzero_ci" for status in symbol_status.values()):
            verdict = "survivor"
        elif all(status == "all_ci_span_zero" for status in symbol_status.values()):
            verdict = "dead"
        else:
            verdict = "insufficient"
        best = _best_score_row(best_rows)
        summary.append(
            {
                "feature": feature_name,
                "verdict": verdict,
                "symbol_status": symbol_status,
                "best_symbol": None if best is None else best["symbol"],
                "best_horizon": None if best is None else best["horizon"],
                "best_level": None if best is None else best.get("level"),
                "best_estimate": None if best is None else best["estimate"],
                "best_ci_low": None if best is None else best["ci_low"],
                "best_ci_high": None if best is None else best["ci_high"],
                "best_bh_q": None if best is None else best.get("bh_q"),
            }
        )
    return summary


def write_ic_screen_outputs(report: Mapping[str, Any], output_dir: Path) -> dict[str, str]:
    """Write JSON, CSV, and markdown evidence for one IC screen."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    scores_path = output_dir / "scores.csv"
    summary_path = output_dir / "SUMMARY.md"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_scores_csv(report.get("scores", []), scores_path)
    summary_path.write_text(summary_markdown(report), encoding="utf-8")
    return {
        "report_json": str(report_path),
        "scores_csv": str(scores_path),
        "summary_md": str(summary_path),
    }


def summary_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# IC feature screen summary",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        (
            f"Scope: symbols `{', '.join(str(symbol) for symbol in report.get('symbols', []))}`, "
            f"tf `{report.get('tf')}`, feature set `{report.get('feature_set')}`, "
            f"horizons `{', '.join(str(h) for h in report.get('horizons', []))}`."
        ),
        "",
        "This is a paper-only pre-registration feature screen. It does not mutate cartridges, unlock Intern, or loosen Track A.",
        "",
        f"CI method: {report.get('ci_note')}",
        "",
        f"Multiple testing: {report.get('multiple_testing_note')}",
        "",
        "| Feature | Verdict | Best evidence | Symbol statuses |",
        "|---|---|---|---|",
    ]
    for row in report.get("kill_summary", []):
        symbol_status = ", ".join(
            f"{symbol}: {status}" for symbol, status in row.get("symbol_status", {}).items()
        )
        level = row.get("best_level")
        level_text = "" if level is None else f" level={level}"
        best = (
            "n/a"
            if row.get("best_symbol") is None
            else (
                f"{row['best_symbol']} h={row['best_horizon']}{level_text} "
                f"est={row['best_estimate']} CI=[{row['best_ci_low']}, {row['best_ci_high']}] "
                f"q={row['best_bh_q']}"
            )
        )
        lines.append(f"| `{row['feature']}` | {row['verdict']} | {best} | {symbol_status} |")
    lines.extend(
        [
            "",
            "Kill rule: dead means every usable CI for both required symbols spans 0. Survivor means only that the feature remains worth a later preregistered bake-off.",
            "",
        ]
    )
    return "\n".join(lines)


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _score_continuous_feature(
    feature_rows: Sequence[Mapping[str, Any]],
    returns: Sequence[float | None],
    *,
    feature_name: str,
    symbol: str,
    tf: str,
    horizon: int,
    min_count: int,
) -> dict[str, Any]:
    pairs = [
        (float(row[feature_name]), float(returns[index]))
        for index, row in enumerate(feature_rows)
        if _is_finite_number(row.get(feature_name)) and _is_finite_number(returns[index])
    ]
    base = _base_score(
        symbol=symbol,
        tf=tf,
        horizon=horizon,
        feature=feature_name,
        feature_kind="continuous",
        level=None,
        statistic="pearson_ic",
        n=len(pairs),
        min_count=min_count,
    )
    if len(pairs) < min_count:
        return base
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    x_std = _population_std(xs, mean=x_mean)
    y_std = _population_std(ys, mean=y_mean)
    if x_std <= 0 or y_std <= 0:
        return base
    products = [((x - x_mean) / x_std) * ((y - y_mean) / y_std) for x, y in pairs]
    stats = hac_mean_stats(products, lags=horizon)
    return _with_stats(base, stats)


def _score_categorical_feature(
    feature_rows: Sequence[Mapping[str, Any]],
    returns: Sequence[float | None],
    *,
    feature_name: str,
    fixed_levels: Sequence[Any] | None,
    symbol: str,
    tf: str,
    horizon: int,
    min_count: int,
) -> list[dict[str, Any]]:
    observed_levels = {
        row.get(feature_name)
        for index, row in enumerate(feature_rows)
        if row.get(feature_name) is not None and _is_finite_number(returns[index])
    }
    levels = list(fixed_levels) if fixed_levels is not None else sorted(observed_levels, key=str)
    scores = []
    for level in levels:
        values = [
            float(returns[index])
            for index, row in enumerate(feature_rows)
            if row.get(feature_name) == level and _is_finite_number(returns[index])
        ]
        base = _base_score(
            symbol=symbol,
            tf=tf,
            horizon=horizon,
            feature=feature_name,
            feature_kind="categorical",
            level=level,
            statistic="conditional_mean_forward_atr_return",
            n=len(values),
            min_count=min_count,
        )
        if len(values) >= min_count:
            base = _with_stats(base, hac_mean_stats(values, lags=horizon))
        scores.append(base)
    return scores


def hac_mean_stats(values: Sequence[float], *, lags: int) -> dict[str, Any]:
    clean = [float(value) for value in values if isfinite(float(value))]
    count = len(clean)
    if count == 0:
        return {
            "estimate": None,
            "ci_low": None,
            "ci_high": None,
            "standard_error": None,
            "p_value": None,
            "ci_lags": 0,
            "ci_spans_zero": True,
        }
    mean = sum(clean) / count
    resolved_lags = min(max(0, int(lags)), count - 1)
    variance = _hac_long_run_variance(clean, mean=mean, lags=resolved_lags)
    standard_error = sqrt(max(variance, 0.0) / count)
    if standard_error <= 0:
        p_value = 0.0 if mean != 0 else 1.0
        ci_low = mean
        ci_high = mean
    else:
        z_score = abs(mean) / standard_error
        p_value = 2.0 * (1.0 - normal_cdf(z_score))
        ci_low = mean - (CI_Z * standard_error)
        ci_high = mean + (CI_Z * standard_error)
    return {
        "estimate": _stable_float(mean),
        "ci_low": _stable_float(ci_low),
        "ci_high": _stable_float(ci_high),
        "standard_error": _stable_float(standard_error),
        "p_value": _stable_float(min(max(p_value, 0.0), 1.0)),
        "ci_lags": resolved_lags,
        "ci_spans_zero": ci_low <= 0 <= ci_high,
    }


def _hac_long_run_variance(values: Sequence[float], *, mean: float, lags: int) -> float:
    count = len(values)
    gamma0 = sum((value - mean) ** 2 for value in values) / count
    variance = gamma0
    for lag in range(1, lags + 1):
        covariance = sum(
            (values[index] - mean) * (values[index - lag] - mean)
            for index in range(lag, count)
        ) / count
        weight = 1.0 - (lag / (lags + 1.0))
        variance += 2.0 * weight * covariance
    return max(variance, 0.0)


def _apply_benjamini_hochberg(scores: list[dict[str, Any]]) -> None:
    indexed = [
        (index, float(score["p_value"]))
        for index, score in enumerate(scores)
        if score.get("p_value") is not None and score.get("enough_data")
    ]
    count = len(indexed)
    for score in scores:
        score["bh_q"] = None
        score["bh_reject_0_05"] = False
    if count == 0:
        return
    ordered = sorted(indexed, key=lambda item: item[1])
    q_values = [1.0] * count
    running_min = 1.0
    for reverse_rank, (score_index, p_value) in enumerate(reversed(ordered), start=1):
        rank = count - reverse_rank + 1
        q_value = min(running_min, p_value * count / rank)
        running_min = q_value
        q_values[rank - 1] = q_value
        scores[score_index]["bh_q"] = _stable_float(q_value)
        scores[score_index]["bh_reject_0_05"] = q_value <= BH_ALPHA


def _base_score(
    *,
    symbol: str,
    tf: str,
    horizon: int,
    feature: str,
    feature_kind: str,
    level: Any,
    statistic: str,
    n: int,
    min_count: int,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "tf": tf,
        "horizon": horizon,
        "feature": feature,
        "feature_kind": feature_kind,
        "level": level,
        "statistic": statistic,
        "n": n,
        "min_count": min_count,
        "enough_data": n >= min_count,
        "estimate": None,
        "ci_low": None,
        "ci_high": None,
        "standard_error": None,
        "p_value": None,
        "ci_method": CI_METHOD,
        "ci_lags": None,
        "ci_spans_zero": True,
    }


def _with_stats(base: dict[str, Any], stats: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(base)
    updated.update(stats)
    updated["enough_data"] = True
    return updated


def _forward_atr_returns(
    closes: Sequence[float],
    atr_values: Sequence[float | None],
    *,
    horizon: int,
) -> list[float | None]:
    returns: list[float | None] = [None] * len(closes)
    for index, close in enumerate(closes):
        future_index = index + horizon
        if future_index >= len(closes):
            continue
        atr = atr_values[index]
        if atr is None or atr <= 0:
            continue
        returns[index] = (closes[future_index] - close) / atr
    return returns


def _window_candles(
    candles: Sequence[Mapping[str, Any]],
    *,
    max_bars: int | None,
    since_ts_ms: int | None,
) -> list[Mapping[str, Any]]:
    windowed = [
        candle
        for candle in candles
        if since_ts_ms is None or int(candle.get("ts_ms", 0)) >= since_ts_ms
    ]
    if max_bars is not None:
        if max_bars <= 0:
            raise ValueError("max_bars must be positive")
        windowed = windowed[-max_bars:]
    return list(windowed)


def _write_scores_csv(scores: Any, path: Path) -> None:
    rows = [dict(score) for score in scores if isinstance(score, Mapping)]
    fieldnames = [
        "symbol",
        "tf",
        "horizon",
        "feature",
        "feature_kind",
        "level",
        "statistic",
        "n",
        "min_count",
        "enough_data",
        "estimate",
        "ci_low",
        "ci_high",
        "standard_error",
        "p_value",
        "bh_q",
        "bh_reject_0_05",
        "ci_method",
        "ci_lags",
        "ci_spans_zero",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _validated_horizons(horizons: Sequence[int]) -> tuple[int, ...]:
    clean = tuple(int(horizon) for horizon in horizons)
    if not clean:
        raise ValueError("at least one horizon is required")
    if any(horizon <= 0 for horizon in clean):
        raise ValueError("horizons must be positive bar counts")
    return clean


def _validated_feature_set(feature_set: str) -> str:
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"feature_set must be one of: {', '.join(FEATURE_SETS)}")
    return feature_set


def _features_for_set(feature_set: str) -> tuple[tuple[str, ...], dict[str, tuple[Any, ...] | None]]:
    safe_feature_set = _validated_feature_set(feature_set)
    if safe_feature_set == "ichimoku":
        return ICHIMOKU_CONTINUOUS_FEATURES, dict(ICHIMOKU_CATEGORICAL_LEVELS)
    if safe_feature_set == "enrichment":
        return ENRICHMENT_CONTINUOUS_FEATURES, dict(ENRICHMENT_CATEGORICAL_LEVELS)
    if safe_feature_set == "all":
        categorical = dict(ICHIMOKU_CATEGORICAL_LEVELS)
        categorical.update(ENRICHMENT_CATEGORICAL_LEVELS)
        return ICHIMOKU_CONTINUOUS_FEATURES + ENRICHMENT_CONTINUOUS_FEATURES, categorical
    raise ValueError(f"unknown feature_set: {feature_set}")


def _feature_contract(feature_set: str) -> dict[str, Any]:
    continuous, categorical = _features_for_set(feature_set)
    return {
        "feature_set": feature_set,
        "continuous": list(continuous),
        "categorical": list(categorical),
        "regime_states": [state.value for state in RegimeState],
        "enrichment_definitions": (
            None
            if feature_set == "ichimoku"
            else {
                "daily_dealing_range": (
                    "latest confirmed strict 3-daily-bar swing high paired with latest "
                    "confirmed strict 3-daily-bar swing low; confirmation waits for the "
                    "next daily candle close"
                ),
                "daily_fvg": (
                    "latest confirmed classic 3-candle daily fair value gap; bullish "
                    "when candle[i].low > candle[i-2].high, bearish when "
                    "candle[i].high < candle[i-2].low"
                ),
                "flat_spanb_overlap": (
                    "existing lookahead-safe displaced Senkou Span B under bar t is "
                    "flat for flat_n bars and lies inside the latest daily FVG"
                ),
            }
        ),
    }


def _symbol_from_candles(candles: Sequence[Mapping[str, Any]]) -> str:
    if not candles:
        raise ValueError("candles must not be empty")
    return validate_symbol(str(candles[0].get("symbol", "")))


def _best_score_row(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: abs(float(row.get("estimate") or 0.0)))


def _cloud_bias(location: Any) -> int | None:
    if location == "above":
        return 1
    if location == "below":
        return -1
    if location == "inside":
        return 0
    return None


def _price_cloud_distance_atr(
    *,
    close: float,
    cloud_top: float | None,
    cloud_bottom: float | None,
    atr: float | None,
) -> float | None:
    if cloud_top is None or cloud_bottom is None or atr is None or atr <= 0:
        return None
    if close > cloud_top:
        return (close - cloud_top) / atr
    if close < cloud_bottom:
        return (close - cloud_bottom) / atr
    return 0.0


def _chikou_gap_atr(
    points: Sequence[Any],
    *,
    index: int,
    displacement: int,
    atr: float | None,
) -> float | None:
    reference_index = index - displacement
    if reference_index < 0 or atr is None or atr <= 0:
        return None
    return (points[index].close - points[reference_index].close) / atr


def _kumo_width_atr(left: float | None, right: float | None, atr: float | None) -> float | None:
    if left is None or right is None or atr is None or atr <= 0:
        return None
    return abs(left - right) / atr


def _spread_atr(left: float | None, right: float | None, atr: float | None) -> float | None:
    if left is None or right is None or atr is None or atr <= 0:
        return None
    return (left - right) / atr


def _spread(left: Any, right: Any) -> float | None:
    if not _is_finite_number(left) or not _is_finite_number(right):
        return None
    return float(left) - float(right)


def _missing_to_none(value: Any) -> Any:
    return None if value == "missing" else value


def _population_std(values: Sequence[float], *, mean: float) -> float:
    if not values:
        return 0.0
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _is_finite_number(value: Any) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _finite_float(raw_value: Any, field_name: str) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _stable_float(value: float) -> float:
    return round(float(value), 10)
