"""Paper-only eval harness helpers."""

from runtime.eval.backtest_ichimoku import (
    BACKTEST_REPORT_SCHEMA,
    BACKTEST_TRADE_SCHEMA,
    backtest_from_store,
    cartridge_backtest_from_store,
    cartridge_oos_backtest_from_store,
    compute_efficiency_ratio,
    compute_wilder_adx,
    resolve_cartridge,
    run_backtest,
    run_backtest_cartridge,
    run_backtest_reference,
    runnable_cartridge_ids,
    signal_for_closed_bar,
    unsupported_cartridge_reasons,
    write_report,
)
from runtime.eval.score_trials import TRIAL_LEDGER_SCHEMA, score_trials, write_summary

__all__ = [
    "BACKTEST_REPORT_SCHEMA",
    "BACKTEST_TRADE_SCHEMA",
    "TRIAL_LEDGER_SCHEMA",
    "backtest_from_store",
    "cartridge_backtest_from_store",
    "cartridge_oos_backtest_from_store",
    "compute_efficiency_ratio",
    "compute_wilder_adx",
    "resolve_cartridge",
    "run_backtest",
    "run_backtest_cartridge",
    "run_backtest_reference",
    "runnable_cartridge_ids",
    "score_trials",
    "signal_for_closed_bar",
    "unsupported_cartridge_reasons",
    "write_report",
    "write_summary",
]
