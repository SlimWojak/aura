"""CLI for the paper-only Aura OHLCV market spine."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from typing import Any, Sequence

from runtime.market import funding_status, read_last_candles, read_last_funding_rates, status
from runtime.market.funding import KrakenCommandError, pull_funding
from runtime.market.ingest import DEFAULT_COUNT, ChartsHTTPError, pull_ohlcv
from runtime.market.symbols import DEFAULT_SYMBOLS, DEFAULT_TFS, OPTIONAL_SYMBOLS, validate_symbol, validate_tf


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    try:
        result = dispatch(args)
    except (ChartsHTTPError, KrakenCommandError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 1


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Ingest and inspect Aura futures OHLCV JSONL.")
    subparsers = parser.add_subparsers(dest="command")

    pull_parser = subparsers.add_parser(
        "pull",
        help="pull Kraken Futures Charts candles into JSONL",
    )
    add_root_arg(pull_parser)
    pull_parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Kraken futures symbol; repeatable; default PF_XBTUSD",
    )
    pull_parser.add_argument(
        "--include-eth",
        action="store_true",
        help="also pull optional PF_ETHUSD when --symbol is not supplied",
    )
    pull_parser.add_argument(
        "--tf",
        action="append",
        dest="tfs",
        help="Charts timeframe; repeatable; default 1h",
    )
    pull_parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Charts count query")
    pull_parser.add_argument("--from-ts", type=int, help="unix seconds lower bound")
    pull_parser.add_argument("--to-ts", type=int, help="unix seconds upper bound")
    pull_parser.add_argument("--timeout-seconds", type=int, default=20, help="HTTPS timeout")

    backfill_parser = subparsers.add_parser(
        "backfill",
        help="page older Kraken Futures Charts candles into JSONL",
    )
    add_root_arg(backfill_parser)
    backfill_parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Kraken futures symbol; repeatable; default PF_XBTUSD",
    )
    backfill_parser.add_argument(
        "--include-eth",
        action="store_true",
        help="also backfill optional PF_ETHUSD when --symbol is not supplied",
    )
    backfill_parser.add_argument(
        "--tf",
        action="append",
        dest="tfs",
        help="Charts timeframe; repeatable; default 1h",
    )
    backfill_parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Charts count query")
    backfill_parser.add_argument("--pages", type=int, default=40, help="maximum pages to fetch")
    backfill_parser.add_argument("--since", help="stop at ISO time, unix seconds, or unix milliseconds")
    backfill_parser.add_argument("--from-ts", type=int, help="unix seconds lower bound")
    backfill_parser.add_argument("--to-ts", type=int, help="unix seconds upper bound")
    backfill_parser.add_argument("--timeout-seconds", type=int, default=20, help="HTTPS timeout")

    funding_parser = subparsers.add_parser(
        "funding-pull",
        help="pull Kraken Futures historical funding rates into JSONL",
    )
    add_root_arg(funding_parser)
    funding_parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Kraken futures symbol; repeatable; default PF_XBTUSD",
    )
    funding_parser.add_argument(
        "--include-eth",
        action="store_true",
        help="also pull optional PF_ETHUSD when --symbol is not supplied",
    )
    funding_parser.add_argument("--kraken-bin", help="override kraken CLI path")

    status_parser = subparsers.add_parser("status", help="show market metadata and file counts")
    add_root_arg(status_parser)

    show_parser = subparsers.add_parser("show", help="show the last N candles")
    add_root_arg(show_parser)
    show_parser.add_argument(
        "--kind",
        choices=("ohlcv", "funding"),
        default="ohlcv",
        help="data kind to show",
    )
    show_parser.add_argument(
        "--funding",
        action="store_true",
        help="shortcut for --kind funding",
    )
    show_parser.add_argument("--symbol", default=DEFAULT_SYMBOLS[0], help="Kraken futures symbol")
    show_parser.add_argument("--tf", default=DEFAULT_TFS[0], help="Charts timeframe")
    show_parser.add_argument("--tail", type=int, default=5, help="number of rows to show")

    return parser


def add_root_arg(parser: ArgumentParser) -> None:
    parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")


def dispatch(args: Namespace) -> dict[str, Any]:
    match args.command:
        case "pull":
            return command_pull(args)
        case "backfill":
            return command_backfill(args)
        case "funding-pull":
            return command_funding_pull(args)
        case "status":
            return command_status(args)
        case "show":
            return command_show(args)
        case _:
            raise ValueError(f"unknown command: {args.command}")


def command_pull(args: Namespace) -> dict[str, Any]:
    pulls: list[dict[str, Any]] = []
    for symbol in selected_symbols(args):
        for tf in selected_tfs(args):
            pulls.append(
                pull_ohlcv(
                    symbol=symbol,
                    tf=tf,
                    aura_root=args.aura_root,
                    count=args.count,
                    from_ts=args.from_ts,
                    to_ts=args.to_ts,
                    timeout_seconds=args.timeout_seconds,
                )
            )
    return {
        "ok": True,
        "pulls": pulls,
    }


def command_backfill(args: Namespace) -> dict[str, Any]:
    pulls: list[dict[str, Any]] = []
    since_ts_ms = parse_since_ts_ms(args.since)
    for symbol in selected_symbols(args):
        for tf in selected_tfs(args):
            pulls.append(
                pull_ohlcv(
                    symbol=symbol,
                    tf=tf,
                    aura_root=args.aura_root,
                    count=args.count,
                    from_ts=args.from_ts,
                    to_ts=args.to_ts,
                    backfill=True,
                    pages=args.pages,
                    since_ts_ms=since_ts_ms,
                    timeout_seconds=args.timeout_seconds,
                )
            )
    return {
        "ok": True,
        "pulls": pulls,
    }


def command_funding_pull(args: Namespace) -> dict[str, Any]:
    pulls: list[dict[str, Any]] = []
    for symbol in selected_symbols(args):
        pulls.append(
            pull_funding(
                symbol=symbol,
                aura_root=args.aura_root,
                kraken_bin=args.kraken_bin,
            )
        )
    return {
        "ok": True,
        "pulls": pulls,
    }


def command_status(args: Namespace) -> dict[str, Any]:
    payload = status(aura_root_override=args.aura_root)
    payload["funding_entries"] = funding_status(aura_root_override=args.aura_root)
    return payload


def command_show(args: Namespace) -> dict[str, Any]:
    symbol = validate_symbol(args.symbol)
    if args.funding:
        args.kind = "funding"
    if args.kind == "funding":
        return {
            "ok": True,
            "kind": "funding",
            "symbol": symbol,
            "tail": args.tail,
            "rates": read_last_funding_rates(
                symbol,
                tail=args.tail,
                aura_root_override=args.aura_root,
            ),
        }
    tf = validate_tf(args.tf)
    return {
        "ok": True,
        "kind": "ohlcv",
        "symbol": symbol,
        "tf": tf,
        "tail": args.tail,
        "candles": read_last_candles(
            symbol,
            tf,
            tail=args.tail,
            aura_root_override=args.aura_root,
        ),
    }


def selected_symbols(args: Namespace) -> tuple[str, ...]:
    if args.symbols:
        return tuple(validate_symbol(symbol) for symbol in args.symbols)
    if args.include_eth:
        return DEFAULT_SYMBOLS + OPTIONAL_SYMBOLS
    return DEFAULT_SYMBOLS


def selected_tfs(args: Namespace) -> tuple[str, ...]:
    if args.tfs:
        return tuple(validate_tf(tf) for tf in args.tfs)
    return DEFAULT_TFS


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


if __name__ == "__main__":
    raise SystemExit(main())
