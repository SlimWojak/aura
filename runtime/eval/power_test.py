"""Synthetic Track A power controls for the Aura paper eval harness."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite, sqrt
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

import json

from runtime.eval.backtest_ichimoku import write_report
from runtime.eval.statistics import (
    DEFAULT_ATR_PERIOD,
    DEFAULT_CSCV_GROUPS,
    RETURN_STATS_SCHEMA,
    compute_wilder_atr,
    periods_per_year_for_tf,
    score_trial_matrix,
    summarize_returns,
)
from runtime.market import ohlcv_path, read_candles, validate_symbol, validate_tf


POWER_TEST_SCHEMA = "aura.track_a_power_test.v1"
POWER_TEST_REPORT_SCHEMA = "aura.track_a_power_test_report.v1"
DEFAULT_EDGE_SHARPE = 0.9
DEFAULT_DSR_THRESHOLD = 0.95
DEFAULT_PBO_THRESHOLD = 0.10
DEFAULT_BLOCK_SIZE = 24
DEFAULT_TRIAL_COUNT = 37
DEFAULT_OOS_SPLIT = 0.7

PowerTestMode = Literal["positive", "negative"]


def run_power_test_from_store(
    *,
    mode: PowerTestMode,
    symbol: str,
    tf: str,
    aura_root: str | Path | None = None,
    fee_bps: float = 4.0,
    oos_split: float = DEFAULT_OOS_SPLIT,
    trial_count: int = DEFAULT_TRIAL_COUNT,
    atr_period: int = DEFAULT_ATR_PERIOD,
    cscv_groups: int = DEFAULT_CSCV_GROUPS,
    edge_sharpe: float = DEFAULT_EDGE_SHARPE,
    block_size: int = DEFAULT_BLOCK_SIZE,
    output_dir: str | Path | None = None,
    regime_tf: str | None = None,
    regime_htf: str | None = None,
) -> dict[str, Any]:
    """Load stored OHLCV, synthesize control reports, and score Track A stats."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    candles = read_candles(safe_symbol, safe_tf, aura_root_override=aura_root)
    result = run_power_test(
        candles,
        mode=mode,
        symbol=safe_symbol,
        tf=safe_tf,
        fee_bps=fee_bps,
        oos_split=oos_split,
        trial_count=trial_count,
        atr_period=atr_period,
        cscv_groups=cscv_groups,
        edge_sharpe=edge_sharpe,
        block_size=block_size,
        output_dir=resolved_output_dir(
            aura_root=aura_root,
            output_dir=output_dir,
            symbol=safe_symbol,
            tf=safe_tf,
            mode=mode,
        ),
        regime_tf=regime_tf,
        regime_htf=regime_htf,
        market_path=str(ohlcv_path(safe_symbol, safe_tf, aura_root_override=aura_root)),
    )
    result["source_candle_count"] = len(candles)
    return result


def run_power_test(
    candles: Sequence[Mapping[str, Any]],
    *,
    mode: PowerTestMode,
    symbol: str,
    tf: str,
    fee_bps: float = 4.0,
    oos_split: float = DEFAULT_OOS_SPLIT,
    trial_count: int = DEFAULT_TRIAL_COUNT,
    atr_period: int = DEFAULT_ATR_PERIOD,
    cscv_groups: int = DEFAULT_CSCV_GROUPS,
    edge_sharpe: float = DEFAULT_EDGE_SHARPE,
    block_size: int = DEFAULT_BLOCK_SIZE,
    output_dir: str | Path,
    regime_tf: str | None = None,
    regime_htf: str | None = None,
    market_path: str | None = None,
) -> dict[str, Any]:
    """Run a positive or negative synthetic-edge control over supplied candles."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    safe_mode = validate_mode(mode)
    split_fraction = validate_fraction(oos_split, "oos_split")
    honest_trial_count = validate_positive_int(trial_count, "trial_count")
    resolved_atr_period = validate_positive_int(atr_period, "atr_period")
    groups = validate_positive_int(cscv_groups, "cscv_groups")
    if groups <= 1 or groups % 2 != 0:
        raise ValueError("cscv_groups must be an even integer greater than 1")
    resolved_block_size = validate_positive_int(block_size, "block_size")
    if honest_trial_count < 2:
        raise ValueError("trial_count must be at least 2 for PBO")
    if not isfinite(float(edge_sharpe)) or edge_sharpe <= 0:
        raise ValueError("edge_sharpe must be a positive finite number")

    base_returns = atr_normalized_close_returns(candles, atr_period=resolved_atr_period)
    if len(base_returns) < groups:
        raise ValueError("not enough ATR-normalized returns for requested CSCV groups")
    split_index = chronological_split_index(len(base_returns), split_fraction)
    scored_returns = base_returns[split_index:]
    if len(scored_returns) < groups:
        raise ValueError("OOS return count is smaller than requested CSCV groups")
    periods_per_year = periods_per_year_for_tf(safe_tf)
    base_noise = standardize(scored_returns)

    reports_dir = Path(output_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    trial_ids, selected_trial_id = write_control_reports(
        mode=safe_mode,
        reports_dir=reports_dir,
        base_noise=base_noise,
        symbol=safe_symbol,
        tf=safe_tf,
        periods_per_year=periods_per_year,
        trial_count=honest_trial_count,
        atr_period=resolved_atr_period,
        fee_bps=fee_bps,
        edge_sharpe=edge_sharpe,
        block_size=resolved_block_size,
    )

    matrix = score_trial_matrix(
        reports_dir,
        trial_count=honest_trial_count,
        groups=groups,
        metric="atr_normalized",
    )
    matrix["n_honest"] = honest_trial_count
    matrix["n_paths"] = len(trial_ids)
    if isinstance(matrix.get("pbo"), dict):
        matrix["pbo"]["n_honest"] = honest_trial_count
        matrix["pbo"]["n_paths"] = len(trial_ids)

    selected = selected_trial(matrix["trials"], selected_trial_id=selected_trial_id)
    best = best_trial(matrix["trials"])
    decision_trial = selected if safe_mode == "positive" else best
    decision_stats = decision_trial["stats"]
    dsr = float(decision_stats["deflated_sharpe_ratio"])
    pbo = float(matrix["pbo"]["pbo"])
    track_a_keep = dsr > DEFAULT_DSR_THRESHOLD and pbo < DEFAULT_PBO_THRESHOLD
    control_passed = track_a_keep if safe_mode == "positive" else not track_a_keep

    output_path = Path(output_dir) / "summary.json"
    result: dict[str, Any] = {
        "schema": POWER_TEST_SCHEMA,
        "ok": control_passed,
        "mode": safe_mode,
        "control_passed": control_passed,
        "track_a_keep": track_a_keep,
        "generated_at": utc_now_iso(),
        "symbol": safe_symbol,
        "tf": safe_tf,
        "market_path": market_path,
        "fee_bps": stable_float(fee_bps),
        "fee_note": "fee_bps is recorded for eval parity; synthetic returns are post-fee controls.",
        "atr_period": resolved_atr_period,
        "oos_split": {
            "fraction": split_fraction,
            "is_return_count": split_index,
            "oos_return_count": len(scored_returns),
        },
        "regime_flags": {
            "regime_tf": regime_tf,
            "regime_htf": regime_htf,
            "note": "accepted for thin-spine CLI parity; injection occurs at return-series level",
        },
        "edge_model": {
            "injection_point": "return_series.series[*].net_atr_normalized_return",
            "positive_edge_period_sharpe": stable_float(edge_sharpe),
            "hypothesis": (
                "The requested Sharpe 0.8-1.0 is treated as period-level "
                "ATR-normalized Sharpe. The report also exposes annualized Sharpe."
            ),
            "negative_control": "block-shuffled and de-meaned ATR-normalized close returns",
        },
        "thresholds": {
            "dsr": DEFAULT_DSR_THRESHOLD,
            "pbo": DEFAULT_PBO_THRESHOLD,
        },
        "n_honest": honest_trial_count,
        "n_paths": len(trial_ids),
        "selected_trial": selected,
        "best_trial": best,
        "decision_trial": decision_trial,
        "matrix": matrix,
        "outputs": {
            "reports_dir": str(reports_dir),
            "summary_json": str(output_path),
        },
    }
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def write_control_reports(
    *,
    mode: PowerTestMode,
    reports_dir: Path,
    base_noise: Sequence[float],
    symbol: str,
    tf: str,
    periods_per_year: float,
    trial_count: int,
    atr_period: int,
    fee_bps: float,
    edge_sharpe: float,
    block_size: int,
) -> tuple[list[str], str]:
    trial_ids = []
    selected_trial_id = f"{mode}-edge"
    for index in range(trial_count):
        if mode == "positive" and index == 0:
            trial_id = selected_trial_id
            returns = [edge_sharpe + value for value in base_noise]
            control = "synthetic_edge"
        elif mode == "positive":
            trial_id = f"positive-null-{index:03d}"
            returns = [0.0 for _ in base_noise]
            control = "null_distractor"
        else:
            trial_id = f"negative-shuffle-{index:03d}"
            shuffled = block_shuffle(base_noise, block_size=block_size, offset=index)
            returns = standardize([value - mean(shuffled) for value in shuffled])
            control = "block_shuffle"
        report = build_synthetic_report(
            trial_id=trial_id,
            control=control,
            returns=returns,
            symbol=symbol,
            tf=tf,
            periods_per_year=periods_per_year,
            trial_count=trial_count,
            atr_period=atr_period,
            fee_bps=fee_bps,
        )
        write_report(report, reports_dir / trial_id)
        trial_ids.append(trial_id)
    if mode == "negative":
        selected_trial_id = trial_ids[0]
    return trial_ids, selected_trial_id


def build_synthetic_report(
    *,
    trial_id: str,
    control: str,
    returns: Sequence[float],
    symbol: str,
    tf: str,
    periods_per_year: float,
    trial_count: int,
    atr_period: int,
    fee_bps: float,
) -> dict[str, Any]:
    rows = [
        {
            "index": index,
            "ts_ms": index * 3_600_000,
            "position": 0,
            "pnl_points": 0.0,
            "simple_return": 0.0,
            "atr_normalized_return": stable_float(value),
            "fee_points": 0.0,
            "fee_simple_return": 0.0,
            "fee_atr_normalized_return": 0.0,
            "net_simple_return": 0.0,
            "net_atr_normalized_return": stable_float(value),
        }
        for index, value in enumerate(returns)
    ]
    zero_returns = [0.0 for _ in returns]
    return {
        "schema": POWER_TEST_REPORT_SCHEMA,
        "ok": True,
        "eval_id": trial_id,
        "generated_at": utc_now_iso(),
        "symbol": symbol,
        "tf": tf,
        "fee_bps": stable_float(fee_bps),
        "control": control,
        "return_series": {
            "schema": RETURN_STATS_SCHEMA,
            "atr_period": atr_period,
            "periods_per_year": stable_float(periods_per_year),
            "trial_count": trial_count,
            "series": rows,
            "summary": {
                "simple": summarize_returns(
                    zero_returns,
                    periods_per_year=periods_per_year,
                    trial_count=trial_count,
                    compound=True,
                ),
                "atr_normalized": summarize_returns(
                    returns,
                    periods_per_year=periods_per_year,
                    trial_count=trial_count,
                    compound=False,
                ),
                "trade_count": 0,
                "return_count": len(returns),
            },
        },
        "trades": [],
    }


def atr_normalized_close_returns(
    candles: Sequence[Mapping[str, Any]],
    *,
    atr_period: int,
) -> list[float]:
    if len(candles) < atr_period + 2:
        raise ValueError("not enough candles to compute ATR-normalized close returns")
    atr_values = compute_wilder_atr(candles, period=atr_period)
    closes = [finite_float(candle.get("close"), f"candles[{index}].close") for index, candle in enumerate(candles)]
    returns = []
    for index in range(1, len(candles)):
        atr_index = index - 1
        atr_value = atr_values[atr_index]
        if atr_value is None or atr_value <= 0:
            atr_value = atr_values[index]
        if atr_value is None or atr_value <= 0:
            continue
        returns.append((closes[index] - closes[index - 1]) / atr_value)
    if not returns:
        raise ValueError("no usable ATR-normalized close returns")
    return returns


def selected_trial(trials: Sequence[Mapping[str, Any]], *, selected_trial_id: str) -> dict[str, Any]:
    for trial in trials:
        if trial["id"] == selected_trial_id:
            return dict(trial)
    raise ValueError(f"selected trial missing from matrix: {selected_trial_id}")


def best_trial(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return dict(max(trials, key=lambda trial: float(trial["stats"]["deflated_sharpe_ratio"])))


def standardize(values: Sequence[float]) -> list[float]:
    if not values:
        raise ValueError("cannot standardize empty values")
    centered = [float(value) - mean(values) for value in values]
    sample_std = stddev(centered)
    if sample_std <= 0:
        return alternating_noise(len(values))
    return [value / sample_std for value in centered]


def alternating_noise(count: int) -> list[float]:
    if count <= 1:
        return [0.0 for _ in range(count)]
    values = [1.0 if index % 2 == 0 else -1.0 for index in range(count)]
    return [value / stddev(values) for value in values]


def block_shuffle(values: Sequence[float], *, block_size: int, offset: int) -> list[float]:
    blocks = [list(values[index : index + block_size]) for index in range(0, len(values), block_size)]
    if not blocks:
        return []
    shift = offset % len(blocks)
    rotated = blocks[shift:] + blocks[:shift]
    if offset % 2:
        rotated = [list(reversed(block)) for block in rotated]
    return [value for block in rotated for value in block]


def resolved_output_dir(
    *,
    aura_root: str | Path | None,
    output_dir: str | Path | None,
    symbol: str,
    tf: str,
    mode: PowerTestMode,
) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    root = Path(aura_root) if aura_root is not None else Path("/var/aura")
    safe_symbol = symbol.lower().replace("_", "-")
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return root / "evidence" / "power_tests" / f"P-track-a-{mode}-{safe_symbol}-{tf}-{stamp}"


def chronological_split_index(count: int, fraction: float) -> int:
    split_index = int(count * fraction)
    if split_index <= 0 or split_index >= count:
        raise ValueError("oos_split leaves an empty IS or OOS return segment")
    return split_index


def validate_mode(mode: str) -> PowerTestMode:
    if mode == "positive" or mode == "negative":
        return mode
    raise ValueError("mode must be 'positive' or 'negative'")


def validate_fraction(value: float, field_name: str) -> float:
    resolved = float(value)
    if not isfinite(resolved) or resolved <= 0 or resolved >= 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return resolved


def validate_positive_int(value: int, field_name: str) -> int:
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"{field_name} must be positive")
    return resolved


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stddev(values: Sequence[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (count - 1)
    return sqrt(max(variance, 0.0))


def finite_float(raw_value: Any, field_name: str) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def stable_float(value: float) -> float:
    return round(float(value), 10)


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
