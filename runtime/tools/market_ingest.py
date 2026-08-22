"""CLI for the paper-only Aura OHLCV market spine."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
import json
from typing import Any, Sequence

from runtime.market import read_last_candles, status
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
    except (ChartsHTTPError, ValueError) as exc:
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

    status_parser = subparsers.add_parser("status", help="show market metadata and file counts")
    add_root_arg(status_parser)

    show_parser = subparsers.add_parser("show", help="show the last N candles")
    add_root_arg(show_parser)
    show_parser.add_argument("--symbol", default=DEFAULT_SYMBOLS[0], help="Kraken futures symbol")
    show_parser.add_argument("--tf", default=DEFAULT_TFS[0], help="Charts timeframe")
    show_parser.add_argument("--tail", type=int, default=5, help="number of candles to show")

    return parser


def add_root_arg(parser: ArgumentParser) -> None:
    parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")


def dispatch(args: Namespace) -> dict[str, Any]:
    match args.command:
        case "pull":
            return command_pull(args)
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


def command_status(args: Namespace) -> dict[str, Any]:
    return status(aura_root_override=args.aura_root)


def command_show(args: Namespace) -> dict[str, Any]:
    symbol = validate_symbol(args.symbol)
    tf = validate_tf(args.tf)
    return {
        "ok": True,
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


if __name__ == "__main__":
    raise SystemExit(main())
