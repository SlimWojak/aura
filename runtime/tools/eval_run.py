"""CLI entrypoint for paper-only Aura eval runs."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from typing import Any, Sequence

from runtime.eval import (
    backtest_from_store,
    cartridge_backtest_from_store,
    runnable_cartridge_ids,
    score_trials,
    write_report,
    write_summary,
)
from runtime.market import DEFAULT_SYMBOLS, DEFAULT_TFS, validate_symbol, validate_tf


DEFAULT_AURA_ROOT = Path("/var/aura")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    try:
        result = dispatch(args)
    except NotImplementedError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "runnable_cartridges": runnable_cartridge_ids(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 1


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run paper-only Aura eval harness commands.")
    subparsers = parser.add_subparsers(dest="command")

    backtest_parser = subparsers.add_parser(
        "backtest",
        help="backtest Ichimoku v0 bias over stored OHLCV",
    )
    add_market_args(backtest_parser)
    backtest_parser.add_argument(
        "--min-bars",
        type=int,
        help="minimum closed candles before scoring; defaults to Ichimoku minimum",
    )
    backtest_parser.add_argument(
        "--max-bars",
        type=int,
        help="score at most the latest N stored candles after --since filtering",
    )
    backtest_parser.add_argument(
        "--since",
        help="score candles at or after ISO time, unix seconds, or unix milliseconds",
    )
    backtest_parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="print compact metrics JSON; full report and trades JSONL are still written",
    )
    backtest_parser.add_argument(
        "--fee-bps",
        type=float,
        default=0.0,
        help="optional per-side fee in basis points for 1-unit price-point accounting",
    )

    cartridge_parser = subparsers.add_parser(
        "cartridge",
        help="backtest a supported research cartridge over stored OHLCV",
    )
    cartridge_source = cartridge_parser.add_mutually_exclusive_group(required=True)
    cartridge_source.add_argument("--id", dest="cartridge_id", help="cartridge id from research/cartridges")
    cartridge_source.add_argument("--path", dest="cartridge_path", help="explicit cartridge YAML path")
    add_market_args(cartridge_parser)
    cartridge_parser.add_argument(
        "--min-bars",
        type=int,
        help="minimum closed candles before scoring; defaults to cartridge Ichimoku minimum",
    )
    cartridge_parser.add_argument(
        "--max-bars",
        type=int,
        help="score at most the latest N stored candles after --since filtering",
    )
    cartridge_parser.add_argument(
        "--since",
        help="score candles at or after ISO time, unix seconds, or unix milliseconds",
    )
    cartridge_parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="print compact metrics JSON; full report and trades JSONL are still written",
    )
    cartridge_parser.add_argument(
        "--fee-bps",
        type=float,
        default=0.0,
        help="optional per-side fee in basis points for 1-unit price-point accounting",
    )
    cartridge_parser.add_argument(
        "--regime-tf",
        help="optional Phase 2 hard-veto regime timeframe resampled from stored 1h OHLCV",
    )
    cartridge_parser.add_argument(
        "--regime-htf",
        default="1d",
        help="optional higher-timeframe regime veto; use 'none' to disable",
    )

    ledger_parser = subparsers.add_parser("ledger", help="rebuild trial ledger summary")
    ledger_parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")

    return parser


def add_market_args(parser: ArgumentParser) -> None:
    parser.add_argument("--symbol", default=DEFAULT_SYMBOLS[0], help="Kraken futures symbol")
    parser.add_argument("--tf", default=DEFAULT_TFS[0], help="stored OHLCV timeframe")
    parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")


def dispatch(args: Namespace) -> dict[str, Any]:
    match args.command:
        case "backtest":
            return command_backtest(args)
        case "cartridge":
            return command_cartridge(args)
        case "ledger":
            return command_ledger(args)
        case _:
            raise ValueError(f"unknown command: {args.command}")


def command_backtest(args: Namespace) -> dict[str, Any]:
    symbol = validate_symbol(args.symbol)
    tf = validate_tf(args.tf)
    report = backtest_from_store(
        symbol=symbol,
        tf=tf,
        aura_root=args.aura_root,
        min_bars=args.min_bars,
        max_bars=args.max_bars,
        since_ts_ms=parse_since_ts_ms(args.since),
        fee_bps=args.fee_bps,
        regime_tf=args.regime_tf,
        regime_htf=parse_optional_tf(args.regime_htf) if args.regime_tf else None,
    )
    eval_id = default_eval_id(symbol=symbol, tf=tf)
    output_dir = evidence_root(args.aura_root) / "evals" / eval_id
    report["eval_id"] = eval_id
    report["outputs"] = {
        "report_json": str(output_dir / "report.json"),
        "trades_jsonl": str(output_dir / "trades.jsonl"),
    }
    outputs = write_report(report, output_dir)
    report["outputs"] = outputs
    if args.metrics_only:
        return metrics_only_report(report)
    return report


def command_cartridge(args: Namespace) -> dict[str, Any]:
    symbol = validate_symbol(args.symbol)
    tf = validate_tf(args.tf)
    report = cartridge_backtest_from_store(
        cartridge_id=args.cartridge_id,
        cartridge_path=args.cartridge_path,
        symbol=symbol,
        tf=tf,
        aura_root=args.aura_root,
        min_bars=args.min_bars,
        max_bars=args.max_bars,
        since_ts_ms=parse_since_ts_ms(args.since),
        fee_bps=args.fee_bps,
    )
    eval_id = default_eval_id(symbol=symbol, tf=tf, cartridge_id=report["cartridge"]["id"])
    output_dir = evidence_root(args.aura_root) / "evals" / eval_id
    report["eval_id"] = eval_id
    report["outputs"] = {
        "report_json": str(output_dir / "report.json"),
        "trades_jsonl": str(output_dir / "trades.jsonl"),
    }
    outputs = write_report(report, output_dir)
    report["outputs"] = outputs
    if args.metrics_only:
        return metrics_only_report(report)
    return report


def command_ledger(args: Namespace) -> dict[str, Any]:
    summary = score_trials(aura_root=args.aura_root)
    output_path = ledger_summary_path(args.aura_root)
    summary["output_path"] = str(output_path)
    write_summary(summary, aura_root=args.aura_root)
    return summary


def evidence_root(aura_root: str | Path | None) -> Path:
    root = Path(aura_root) if aura_root is not None else Path(os.environ.get("AURA_ROOT", str(DEFAULT_AURA_ROOT)))
    return root / "evidence"


def ledger_summary_path(aura_root: str | Path | None) -> Path:
    return evidence_root(aura_root) / "ledger" / "summary.json"


def default_eval_id(*, symbol: str, tf: str, cartridge_id: str | None = None) -> str:
    safe_symbol = symbol.lower().replace("_", "-")
    suffix = f"{cartridge_id}-" if cartridge_id is not None else ""
    return f"E-ichi-{suffix}{safe_symbol}-{tf}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}"


def parse_since_ts_ms(raw_since: str | None) -> int | None:
    if raw_since is None:
        return None
    raw_text = raw_since.strip()
    if not raw_text:
        raise ValueError("--since must not be empty")
    try:
        value = Decimal(raw_text)
    except InvalidOperation:
        iso_text = raw_text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_text)
        except ValueError as exc:
            raise ValueError("--since must be ISO time, unix seconds, or unix milliseconds") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return int(parsed.timestamp() * 1000)
    if not value.is_finite() or value <= 0:
        raise ValueError("--since must be a positive timestamp")
    if value > Decimal("100000000000"):
        return int(value)
    return int(value * 1000)


def metrics_only_report(report: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema",
        "ok",
        "reason",
        "generated_at",
        "eval_id",
        "symbol",
        "tf",
        "market_path",
        "source_candle_count",
        "candle_count",
        "evaluated_bars",
        "min_bars",
        "params",
        "fee_bps",
        "fee_assumption",
        "fee_model",
        "cartridge",
        "regime_gate",
        "engine",
        "window",
        "metrics",
        "outputs",
    )
    return {key: report[key] for key in keys if key in report}


def parse_optional_tf(raw_tf: str | None) -> str | None:
    if raw_tf is None or raw_tf.strip().lower() in {"", "none", "off", "false"}:
        return None
    return validate_tf(raw_tf)


if __name__ == "__main__":
    raise SystemExit(main())
