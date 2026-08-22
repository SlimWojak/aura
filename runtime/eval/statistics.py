"""Return-path and trial-adjusted statistics for Aura paper evals."""

from __future__ import annotations

from itertools import combinations
from math import erf, exp, isfinite, log, sqrt
from pathlib import Path
import json
from statistics import NormalDist
from typing import Any, Mapping, Sequence


RETURN_STATS_SCHEMA = "aura.return_stats.v1"
TRIAL_MATRIX_SCHEMA = "aura.trial_matrix_stats.v1"
DEFAULT_ATR_PERIOD = 14
DEFAULT_CSCV_GROUPS = 8
EULER_GAMMA = 0.5772156649015329


def compute_wilder_atr(
    candles: Sequence[Mapping[str, Any]],
    *,
    period: int = DEFAULT_ATR_PERIOD,
) -> list[float | None]:
    """Compute Wilder ATR aligned to input candles."""

    if period <= 0:
        raise ValueError("ATR period must be positive")
    count = len(candles)
    atr: list[float | None] = [None] * count
    if count == 0:
        return atr

    highs = [_finite_float(candle.get("high"), f"candles[{index}].high") for index, candle in enumerate(candles)]
    lows = [_finite_float(candle.get("low"), f"candles[{index}].low") for index, candle in enumerate(candles)]
    closes = [_finite_float(candle.get("close"), f"candles[{index}].close") for index, candle in enumerate(candles)]
    true_ranges = [0.0] * count
    true_ranges[0] = highs[0] - lows[0]
    for index in range(1, count):
        true_ranges[index] = max(
            highs[index] - lows[index],
            abs(highs[index] - closes[index - 1]),
            abs(lows[index] - closes[index - 1]),
        )

    if count < period:
        return atr
    first_atr = sum(true_ranges[:period]) / period
    atr[period - 1] = first_atr
    previous = first_atr
    for index in range(period, count):
        previous = ((previous * (period - 1)) + true_ranges[index]) / period
        atr[index] = previous
    return atr


def build_return_report(
    candles: Sequence[Mapping[str, Any]],
    trades: Sequence[Mapping[str, Any]],
    *,
    start_index: int,
    tf: str,
    fee_bps: float = 0.0,
    atr_period: int = DEFAULT_ATR_PERIOD,
    trial_count: int = 1,
) -> dict[str, Any]:
    """Build path data and summary metrics from closed point-PnL trades."""

    if start_index < 0:
        raise ValueError("start_index must be nonnegative")
    if atr_period <= 0:
        raise ValueError("atr_period must be positive")
    if trial_count <= 0:
        raise ValueError("trial_count must be positive")

    atr_values = compute_wilder_atr(candles, period=atr_period)
    rows = [
        {
            "index": index,
            "ts_ms": candles[index].get("ts_ms"),
            "close": _stable_float(_finite_float(candles[index].get("close"), f"candles[{index}].close")),
            "atr": _stable_optional(atr_values[index]),
            "position": 0,
            "pnl_points": 0.0,
            "simple_return": 0.0,
            "atr_normalized_return": 0.0,
            "fee_points": 0.0,
            "fee_simple_return": 0.0,
            "fee_atr_normalized_return": 0.0,
            "net_simple_return": 0.0,
            "net_atr_normalized_return": 0.0,
        }
        for index in range(start_index, len(candles))
    ]
    rows_by_index = {int(row["index"]): row for row in rows}

    total_fee_points = 0.0
    fee_simple_return = 0.0
    fee_atr_return = 0.0
    holding_bars: list[int] = []
    position_changes = 0
    previous_direction = 0
    for trade in trades:
        direction = _direction_from_trade(trade)
        entry_index = int(trade["entry_index"])
        exit_index = int(trade["exit_index"])
        entry_price = _finite_float(trade["entry_price"], "trade.entry_price")
        exit_price = _finite_float(trade["exit_price"], "trade.exit_price")
        fee_points = _finite_float(trade.get("fee_points", 0.0), "trade.fee_points")
        total_fee_points += fee_points
        holding_bars.append(max(0, exit_index - entry_index + 1))
        if previous_direction != direction:
            position_changes += 1
        previous_direction = direction

        for index in range(max(entry_index, start_index), min(exit_index, len(candles) - 1) + 1):
            row = rows_by_index.get(index)
            if row is None:
                continue
            previous_price = (
                entry_price
                if index == entry_index
                else _finite_float(candles[index - 1].get("close"), f"candles[{index - 1}].close")
            )
            current_price = (
                exit_price
                if index == exit_index
                else _finite_float(candles[index].get("close"), f"candles[{index}].close")
            )
            atr_risk = _atr_risk_for_bar(atr_values, index)
            pnl_points = direction * (current_price - previous_price)
            simple_return = pnl_points / previous_price if previous_price > 0 else 0.0
            atr_return = pnl_points / atr_risk if atr_risk is not None else 0.0
            row["position"] = direction
            row["pnl_points"] = _stable_float(float(row["pnl_points"]) + pnl_points)
            row["simple_return"] = _stable_float(float(row["simple_return"]) + simple_return)
            row["atr_normalized_return"] = _stable_float(
                float(row["atr_normalized_return"]) + atr_return
            )

        exit_row = rows_by_index.get(exit_index)
        if exit_row is not None and fee_points > 0:
            fee_basis_price = max(entry_price, 1e-12)
            fee_atr_risk = _atr_risk_for_bar(atr_values, exit_index)
            trade_fee_simple = fee_points / fee_basis_price
            trade_fee_atr = fee_points / fee_atr_risk if fee_atr_risk is not None else 0.0
            fee_simple_return += trade_fee_simple
            fee_atr_return += trade_fee_atr
            exit_row["fee_points"] = _stable_float(float(exit_row["fee_points"]) + fee_points)
            exit_row["fee_simple_return"] = _stable_float(
                float(exit_row["fee_simple_return"]) + trade_fee_simple
            )
            exit_row["fee_atr_normalized_return"] = _stable_float(
                float(exit_row["fee_atr_normalized_return"]) + trade_fee_atr
            )

    for row in rows:
        row["net_simple_return"] = _stable_float(
            float(row["simple_return"]) - float(row["fee_simple_return"])
        )
        row["net_atr_normalized_return"] = _stable_float(
            float(row["atr_normalized_return"]) - float(row["fee_atr_normalized_return"])
        )

    periods_per_year = periods_per_year_for_tf(tf)
    simple_returns = [float(row["net_simple_return"]) for row in rows]
    atr_returns = [float(row["net_atr_normalized_return"]) for row in rows]
    gross_simple_returns = [float(row["simple_return"]) for row in rows]
    gross_atr_returns = [float(row["atr_normalized_return"]) for row in rows]
    evaluated_bars = len(rows)
    trade_count = len(trades)
    turnover = position_changes / evaluated_bars if evaluated_bars else 0.0
    average_holding_period = sum(holding_bars) / trade_count if trade_count else 0.0

    return {
        "schema": RETURN_STATS_SCHEMA,
        "atr_period": atr_period,
        "periods_per_year": _stable_float(periods_per_year),
        "trial_count": trial_count,
        "series": rows,
        "summary": {
            "simple": summarize_returns(
                simple_returns,
                periods_per_year=periods_per_year,
                trial_count=trial_count,
                compound=True,
            ),
            "atr_normalized": summarize_returns(
                atr_returns,
                periods_per_year=periods_per_year,
                trial_count=trial_count,
                compound=False,
            ),
            "gross_simple": summarize_returns(
                gross_simple_returns,
                periods_per_year=periods_per_year,
                trial_count=trial_count,
                compound=True,
            ),
            "gross_atr_normalized": summarize_returns(
                gross_atr_returns,
                periods_per_year=periods_per_year,
                trial_count=trial_count,
                compound=False,
            ),
            "trade_count": trade_count,
            "average_holding_bars": _stable_float(average_holding_period),
            "turnover": _stable_float(turnover),
            "fee_bps": _stable_float(fee_bps),
            "fee_drag_points": _stable_float(total_fee_points),
            "fee_drag_simple_return": _stable_float(fee_simple_return),
            "fee_drag_atr_normalized_return": _stable_float(fee_atr_return),
            "return_count": len(rows),
        },
    }


def summarize_returns(
    returns: Sequence[float],
    *,
    periods_per_year: float,
    trial_count: int = 1,
    compound: bool = True,
) -> dict[str, Any]:
    """Summarize a return stream with PSR and DSR."""

    clean = [float(value) for value in returns if isfinite(float(value))]
    count = len(clean)
    cumulative_sum = sum(clean)
    total_return = _compound_return(clean) if compound else cumulative_sum
    mean = sum(clean) / count if count else 0.0
    sample_std = _sample_std(clean)
    period_sharpe = mean / sample_std if sample_std > 0 else 0.0
    annualized_sharpe = period_sharpe * sqrt(periods_per_year)
    skewness = _skewness(clean, mean=mean, sample_std=sample_std)
    raw_kurtosis = _raw_kurtosis(clean, mean=mean, sample_std=sample_std)
    max_drawdown = _max_drawdown(clean) if compound else _additive_max_drawdown(clean)
    annualized_return = (
        _annualized_return(total_return, count=count, periods_per_year=periods_per_year)
        if compound
        else mean * periods_per_year
    )
    calmar = annualized_return / abs(max_drawdown) if max_drawdown < 0 else None
    lo = lo_sharpe_standard_error(clean, period_sharpe=period_sharpe, periods_per_year=periods_per_year)
    psr = probabilistic_sharpe_ratio(
        period_sharpe,
        benchmark_sharpe=0.0,
        sample_count=count,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
    )
    dsr = deflated_sharpe_ratio(
        period_sharpe,
        sample_count=count,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
        trial_count=trial_count,
    )
    return {
        "count": count,
        "path_type": "compound" if compound else "additive",
        "mean_return": _stable_float(mean),
        "sample_std": _stable_float(sample_std),
        "total_return": _stable_float(total_return),
        "cumulative_return_sum": _stable_float(cumulative_sum),
        "annualized_return": _stable_float(annualized_return),
        "period_sharpe": _stable_float(period_sharpe),
        "annualized_sharpe": _stable_float(annualized_sharpe),
        "lo_autocorr_lags": lo["lags"],
        "lo_variance_inflation": _stable_float(lo["variance_inflation"]),
        "lo_annualized_sharpe_se": _stable_float(lo["annualized_sharpe_se"]),
        "probabilistic_sharpe_sr0": _stable_float(psr),
        "deflated_sharpe_ratio": _stable_float(dsr["probability"]),
        "dsr_benchmark_sharpe": _stable_float(dsr["benchmark_sharpe"]),
        "dsr_trial_count": trial_count,
        "skew": _stable_float(skewness),
        "kurtosis": _stable_float(raw_kurtosis),
        "excess_kurtosis": _stable_float(raw_kurtosis - 3.0),
        "max_drawdown_return": _stable_float(max_drawdown),
        "calmar_mar": None if calmar is None else _stable_float(calmar),
    }


def probabilistic_sharpe_ratio(
    sharpe: float,
    *,
    benchmark_sharpe: float,
    sample_count: int,
    skewness: float,
    raw_kurtosis: float,
) -> float:
    """Return PSR probability that true Sharpe exceeds the benchmark."""

    if sample_count < 2:
        return 0.5
    denominator = 1.0 - (skewness * sharpe) + (((raw_kurtosis - 1.0) / 4.0) * sharpe * sharpe)
    if denominator <= 0 or not isfinite(denominator):
        return 1.0 if sharpe > benchmark_sharpe else 0.0
    z_score = (sharpe - benchmark_sharpe) * sqrt(sample_count - 1) / sqrt(denominator)
    return normal_cdf(z_score)


def deflated_sharpe_ratio(
    sharpe: float,
    *,
    sample_count: int,
    skewness: float,
    raw_kurtosis: float,
    trial_count: int,
) -> dict[str, float]:
    """Return DSR as PSR against the expected maximum Sharpe across trials."""

    if trial_count <= 1:
        benchmark = 0.0
    else:
        denominator = 1.0 - (skewness * sharpe) + (((raw_kurtosis - 1.0) / 4.0) * sharpe * sharpe)
        variance_sharpe = max(denominator / max(sample_count - 1, 1), 0.0)
        expected_max_z = (
            (1.0 - EULER_GAMMA) * normal_ppf(1.0 - (1.0 / trial_count))
            + EULER_GAMMA * normal_ppf(1.0 - (1.0 / (trial_count * exp(1.0))))
        )
        benchmark = sqrt(variance_sharpe) * expected_max_z
    probability = probabilistic_sharpe_ratio(
        sharpe,
        benchmark_sharpe=benchmark,
        sample_count=sample_count,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
    )
    return {"probability": probability, "benchmark_sharpe": benchmark}


def probability_of_backtest_overfitting(
    trials: Sequence[Mapping[str, Any]],
    *,
    groups: int = DEFAULT_CSCV_GROUPS,
    metric: str = "sharpe",
    purge_groups: int = 0,
    embargo_groups: int = 0,
) -> dict[str, Any]:
    """Compute PBO using Combinatorially Symmetric Cross-Validation."""

    if groups <= 1 or groups % 2 != 0:
        raise ValueError("CSCV groups must be an even integer greater than 1")
    if purge_groups < 0:
        raise ValueError("purge_groups must be nonnegative")
    if embargo_groups < 0:
        raise ValueError("embargo_groups must be nonnegative")
    prepared = [_prepared_trial(trial) for trial in trials]
    if len(prepared) < 2:
        raise ValueError("PBO requires at least two trials")
    sample_count = min(len(trial["returns"]) for trial in prepared)
    if sample_count < groups:
        raise ValueError("not enough return observations for requested CSCV groups")
    group_indexes = _cscv_group_indexes(sample_count, groups)
    split_rows = []
    for is_groups_tuple in combinations(range(groups), groups // 2):
        is_groups = set(is_groups_tuple)
        oos_groups = set(range(groups)) - is_groups
        purged_is_groups = _purged_is_groups(
            is_groups,
            oos_groups,
            groups=groups,
            purge_groups=purge_groups,
            embargo_groups=embargo_groups,
        )
        if not purged_is_groups:
            continue
        is_indexes = _indexes_for_groups(group_indexes, purged_is_groups)
        oos_indexes = _indexes_for_groups(group_indexes, oos_groups)
        if not is_indexes or not oos_indexes:
            continue
        is_scores = [
            _performance_score(_select_indexes(trial["returns"], is_indexes), metric=metric)
            for trial in prepared
        ]
        oos_scores = [
            _performance_score(_select_indexes(trial["returns"], oos_indexes), metric=metric)
            for trial in prepared
        ]
        winner_index = max(range(len(prepared)), key=lambda index: is_scores[index])
        oos_rank = _rank_from_worst(oos_scores, winner_index)
        omega = oos_rank / (len(prepared) + 1)
        lambda_logit = log(omega / (1.0 - omega))
        split_rows.append(
            {
                "is_groups": sorted(is_groups),
                "oos_groups": sorted(oos_groups),
                "purged_is_groups": sorted(purged_is_groups),
                "winner": prepared[winner_index]["id"],
                "is_score": _stable_float(is_scores[winner_index]),
                "oos_score": _stable_float(oos_scores[winner_index]),
                "oos_rank_from_worst": oos_rank,
                "omega": _stable_float(omega),
                "lambda_logit": _stable_float(lambda_logit),
                "overfit": lambda_logit < 0,
            }
        )
    split_count = len(split_rows)
    if split_count == 0:
        raise ValueError("CSCV produced no usable splits")
    overfit_count = sum(1 for row in split_rows if row["overfit"])
    return {
        "groups": groups,
        "metric": metric,
        "purge_groups": purge_groups,
        "embargo_groups": embargo_groups,
        "trial_count": len(prepared),
        "sample_count": sample_count,
        "split_count": split_count,
        "overfit_count": overfit_count,
        "pbo": _stable_float(overfit_count / split_count),
        "logits": split_rows,
    }


def score_trial_matrix(
    reports_dir: str | Path,
    *,
    trial_count: int | None = None,
    groups: int = DEFAULT_CSCV_GROUPS,
    metric: str = "atr_normalized",
    purge_groups: int = 0,
    embargo_groups: int = 0,
) -> dict[str, Any]:
    """Load saved report.json files and compute DSR/PBO over their return paths."""

    root = Path(reports_dir)
    if not root.exists():
        raise ValueError(f"reports directory does not exist: {root}")
    trials = []
    for report_path in sorted(root.rglob("report.json")):
        report = json.loads(report_path.read_text(encoding="utf-8"))
        extracted = extract_trial_returns(report, source_path=report_path, metric=metric)
        if extracted is not None:
            trials.append(extracted)
    if len(trials) < 2:
        raise ValueError("matrix scoring requires at least two saved reports with return_series")
    resolved_trial_count = trial_count if trial_count is not None else len(trials)
    if resolved_trial_count < len(trials):
        raise ValueError("--trial-count must be >= the number of report files scored")
    periods_per_year = _finite_float(trials[0]["periods_per_year"], "periods_per_year")
    trial_summaries = []
    for trial in trials:
        stats = summarize_returns(
            trial["returns"],
            periods_per_year=periods_per_year,
            trial_count=resolved_trial_count,
            compound=(metric == "simple"),
        )
        trial_summaries.append(
            {
                "id": trial["id"],
                "source_path": trial["source_path"],
                "return_count": len(trial["returns"]),
                "stats": stats,
            }
        )
    pbo = probability_of_backtest_overfitting(
        trials,
        groups=groups,
        metric="sharpe",
        purge_groups=purge_groups,
        embargo_groups=embargo_groups,
    )
    pbo["n_paths"] = len(trials)
    pbo["n_honest"] = resolved_trial_count
    return {
        "schema": TRIAL_MATRIX_SCHEMA,
        "ok": True,
        "reports_dir": str(root),
        "metric": metric,
        "trial_count": resolved_trial_count,
        "n_honest": resolved_trial_count,
        "n_paths": len(trials),
        "reports_scored": len(trials),
        "dsr_note": "n_honest must count every tried parameter variant, not only runnable paths",
        "pbo": pbo,
        "trials": trial_summaries,
    }


def extract_trial_returns(
    report: Mapping[str, Any],
    *,
    source_path: Path,
    metric: str,
) -> dict[str, Any] | None:
    """Extract one trial's saved return stream from a report."""

    return_report = report.get("return_series")
    if not isinstance(return_report, Mapping):
        return None
    series = return_report.get("series")
    if not isinstance(series, list):
        return None
    field = "net_atr_normalized_return" if metric == "atr_normalized" else "net_simple_return"
    returns = [
        _finite_float(row.get(field), f"{source_path}:{field}")
        for row in series
        if isinstance(row, Mapping)
    ]
    if not returns:
        return None
    trial_id = str(report.get("eval_id") or report.get("cartridge", {}).get("id") or source_path.parent.name)
    return {
        "id": trial_id,
        "source_path": str(source_path),
        "returns": returns,
        "periods_per_year": return_report.get("periods_per_year", periods_per_year_for_tf(str(report.get("tf", "1h")))),
    }


def periods_per_year_for_tf(tf: str) -> float:
    if tf.endswith("m"):
        minutes = int(tf[:-1])
        return (365.0 * 24.0 * 60.0) / minutes
    if tf.endswith("h"):
        hours = int(tf[:-1])
        return (365.0 * 24.0) / hours
    if tf.endswith("d"):
        days = int(tf[:-1])
        return 365.0 / days
    raise ValueError(f"unsupported timeframe for annualization: {tf!r}")


def lo_sharpe_standard_error(
    returns: Sequence[float],
    *,
    period_sharpe: float,
    periods_per_year: float,
) -> dict[str, float | int]:
    count = len(returns)
    if count < 2:
        return {"lags": 0, "variance_inflation": 1.0, "annualized_sharpe_se": 0.0}
    lags = min(12, count - 1)
    autocorr_sum = sum(_autocorrelation(returns, lag) for lag in range(1, lags + 1))
    variance_inflation = max(1.0 + (2.0 * autocorr_sum), 1e-12)
    annualized_se = sqrt(periods_per_year) * sqrt(variance_inflation / count)
    if not isfinite(period_sharpe):
        annualized_se = 0.0
    return {
        "lags": lags,
        "variance_inflation": variance_inflation,
        "annualized_sharpe_se": annualized_se,
    }


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def normal_ppf(probability: float) -> float:
    clipped = min(max(probability, 1e-12), 1.0 - 1e-12)
    return NormalDist().inv_cdf(clipped)


def _prepared_trial(trial: Mapping[str, Any]) -> dict[str, Any]:
    trial_id = str(trial.get("id", "unknown"))
    returns = [_finite_float(value, f"{trial_id}.returns") for value in trial.get("returns", [])]
    if not returns:
        raise ValueError(f"trial {trial_id} has no returns")
    return {"id": trial_id, "returns": returns}


def _performance_score(returns: Sequence[float], *, metric: str) -> float:
    if metric == "mean":
        return sum(returns) / len(returns) if returns else 0.0
    if metric == "sharpe":
        mean = sum(returns) / len(returns) if returns else 0.0
        std = _sample_std(returns)
        return mean / std if std > 0 else 0.0
    raise ValueError(f"unsupported CSCV metric: {metric}")


def _cscv_group_indexes(sample_count: int, groups: int) -> list[list[int]]:
    base = sample_count // groups
    remainder = sample_count % groups
    result = []
    start = 0
    for group in range(groups):
        size = base + (1 if group < remainder else 0)
        result.append(list(range(start, start + size)))
        start += size
    return result


def _purged_is_groups(
    is_groups: set[int],
    oos_groups: set[int],
    *,
    groups: int,
    purge_groups: int,
    embargo_groups: int,
) -> set[int]:
    removed: set[int] = set()
    for oos_group in oos_groups:
        for distance in range(1, purge_groups + 1):
            removed.add(oos_group - distance)
            removed.add(oos_group + distance)
        for distance in range(1, embargo_groups + 1):
            removed.add(oos_group + distance)
    valid_removed = {group for group in removed if 0 <= group < groups}
    return is_groups - valid_removed


def _indexes_for_groups(group_indexes: Sequence[Sequence[int]], groups: set[int]) -> list[int]:
    indexes: list[int] = []
    for group in sorted(groups):
        indexes.extend(group_indexes[group])
    return indexes


def _select_indexes(values: Sequence[float], indexes: Sequence[int]) -> list[float]:
    return [values[index] for index in indexes]


def _rank_from_worst(scores: Sequence[float], selected_index: int) -> int:
    selected_score = scores[selected_index]
    return 1 + sum(1 for score in scores if score < selected_score)


def _direction_from_trade(trade: Mapping[str, Any]) -> int:
    direction = str(trade.get("direction"))
    if direction == "long":
        return 1
    if direction == "short":
        return -1
    raise ValueError(f"unsupported trade direction: {direction!r}")


def _atr_risk_for_bar(atr_values: Sequence[float | None], index: int) -> float | None:
    risk_index = max(0, index - 1)
    atr_value = atr_values[risk_index]
    if atr_value is None or atr_value <= 0:
        atr_value = atr_values[index] if index < len(atr_values) else None
    return atr_value if atr_value is not None and atr_value > 0 else None


def _compound_return(returns: Sequence[float]) -> float:
    compounded = 1.0
    for value in returns:
        compounded *= 1.0 + value
    return compounded - 1.0


def _annualized_return(total_return: float, *, count: int, periods_per_year: float) -> float:
    if count <= 0:
        return 0.0
    if total_return <= -1.0:
        return -1.0
    return (1.0 + total_return) ** (periods_per_year / count) - 1.0


def _max_drawdown(returns: Sequence[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = (equity / peak) - 1.0 if peak > 0 else 0.0
        max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown


def _additive_max_drawdown(returns: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    return max_drawdown


def _sample_std(values: Sequence[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return sqrt(max(variance, 0.0))


def _skewness(values: Sequence[float], *, mean: float, sample_std: float) -> float:
    count = len(values)
    if count < 3 or sample_std <= 0:
        return 0.0
    return sum(((value - mean) / sample_std) ** 3 for value in values) / count


def _raw_kurtosis(values: Sequence[float], *, mean: float, sample_std: float) -> float:
    count = len(values)
    if count < 4 or sample_std <= 0:
        return 3.0
    return sum(((value - mean) / sample_std) ** 4 for value in values) / count


def _autocorrelation(values: Sequence[float], lag: int) -> float:
    count = len(values)
    if lag <= 0 or lag >= count:
        return 0.0
    mean = sum(values) / count
    denominator = sum((value - mean) ** 2 for value in values)
    if denominator <= 0:
        return 0.0
    numerator = sum((values[index] - mean) * (values[index - lag] - mean) for index in range(lag, count))
    return numerator / denominator


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


def _stable_optional(value: float | None) -> float | None:
    return None if value is None else _stable_float(value)
