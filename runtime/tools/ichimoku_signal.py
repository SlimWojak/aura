"""CLI for Aura Ichimoku v0 signal-only brain evidence."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from runtime.brain import BRAIN_SIGNAL_SCHEMA, compute_ichimoku, signal_from_series
from runtime.brain.types import IchimokuSignal
from runtime.evidence import decision_jsonl_path
from runtime.market import DEFAULT_SYMBOLS, DEFAULT_TFS, ohlcv_path, read_candles, validate_symbol, validate_tf
from runtime.runner import run_supervised_order
from runtime.runner.supervised_paper import DEFAULT_LEVERAGE, DEFAULT_ORDER_TYPE, DEFAULT_SIZE


DEFAULT_ACTOR = "cos:ichimoku_v0"
DEFAULT_HYPOTHESIS_ID = "ichi-v0"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    try:
        result = dispatch(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 1


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Compute Aura Ichimoku v0 from stored OHLCV JSONL.")
    subparsers = parser.add_subparsers(dest="command")

    compute_parser = subparsers.add_parser("compute", help="print latest Ichimoku components and bias")
    add_market_args(compute_parser)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="append brain signal evidence JSONL and optionally dry-propose a paper order",
    )
    add_market_args(evaluate_parser)
    evaluate_parser.add_argument("--trial-id", help="override evidence trial id")
    evaluate_parser.add_argument("--actor", default=DEFAULT_ACTOR, help="actor label for evidence")
    evaluate_parser.add_argument(
        "--hypothesis-id",
        default=DEFAULT_HYPOTHESIS_ID,
        help="hypothesis id attached to the brain signal event",
    )
    evaluate_parser.add_argument(
        "--propose-paper",
        action="store_true",
        help="map long/short bias into a supervised futures-paper proposal",
    )
    evaluate_parser.add_argument(
        "--i-understand-paper",
        action="store_true",
        help="with --propose-paper, allow an actual futures-paper order after admit",
    )
    evaluate_parser.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help="paper proposal size; default is the supervised runner's tiny size",
    )
    evaluate_parser.add_argument(
        "--leverage",
        default=DEFAULT_LEVERAGE,
        help="paper proposal leverage; still capped by runtime.risk.admit",
    )
    evaluate_parser.add_argument(
        "--order-type",
        default=DEFAULT_ORDER_TYPE,
        help="paper proposal order type",
    )
    evaluate_parser.add_argument(
        "--notional-usd",
        help="paper proposal notional; default derives size * latest close",
    )
    evaluate_parser.add_argument("--client-order-id", help="override paper client order id")

    return parser


def add_market_args(parser: ArgumentParser) -> None:
    parser.add_argument("--symbol", default=DEFAULT_SYMBOLS[0], help="Kraken futures symbol")
    parser.add_argument("--tf", default=DEFAULT_TFS[0], help="stored OHLCV timeframe")
    parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")


def dispatch(args: Namespace) -> dict[str, Any]:
    match args.command:
        case "compute":
            return command_compute(args)
        case "evaluate":
            return command_evaluate(args)
        case _:
            raise ValueError(f"unknown command: {args.command}")


def command_compute(args: Namespace) -> dict[str, Any]:
    candles, signal = read_signal(args)
    payload = signal.to_dict()
    payload.update(
        {
            "symbol": validate_symbol(args.symbol),
            "tf": validate_tf(args.tf),
            "candle_count": len(candles),
            "market_path": str(
                ohlcv_path(args.symbol, args.tf, aura_root_override=args.aura_root)
            ),
        }
    )
    return payload


def command_evaluate(args: Namespace) -> dict[str, Any]:
    candles, signal = read_signal(args)
    symbol = validate_symbol(args.symbol)
    tf = validate_tf(args.tf)
    trial_id = args.trial_id or default_trial_id(symbol=symbol, tf=tf)
    paper_summary = maybe_propose_paper(args=args, signal=signal, trial_id=trial_id, symbol=symbol)
    event = build_brain_signal_event(
        trial_id=trial_id,
        actor=args.actor,
        hypothesis_id=args.hypothesis_id,
        symbol=symbol,
        tf=tf,
        candles=candles,
        aura_root=args.aura_root,
        signal=signal,
        paper_summary=paper_summary,
    )
    evidence_path = append_jsonl(
        decision_jsonl_path(trial_id, aura_root=args.aura_root, repo_fallback=False),
        event,
    )
    return {
        "ok": signal.ok,
        "trial_id": trial_id,
        "decision_jsonl": str(evidence_path),
        "signal": signal.to_dict(),
        "paper": paper_summary,
    }


def read_signal(args: Namespace) -> tuple[list[dict[str, Any]], IchimokuSignal]:
    symbol = validate_symbol(args.symbol)
    tf = validate_tf(args.tf)
    candles = read_candles(symbol, tf, aura_root_override=args.aura_root)
    series = compute_ichimoku(candles)
    return candles, signal_from_series(series)


def maybe_propose_paper(
    *,
    args: Namespace,
    signal: IchimokuSignal,
    trial_id: str,
    symbol: str,
) -> dict[str, Any]:
    dry_run = not args.i_understand_paper
    if not args.propose_paper:
        return {"requested": False}
    if not signal.ok:
        return {"requested": True, "called": False, "reason": signal.reason, "dry_run": dry_run}
    if signal.bias == "flat":
        return {
            "requested": True,
            "called": False,
            "reason": "flat_bias_no_op",
            "dry_run": dry_run,
        }

    side = "buy" if signal.bias == "long" else "sell"
    client_order_id = args.client_order_id or default_client_order_id(
        bias=signal.bias,
        symbol=symbol,
        ts_ms=signal.ts_ms,
    )
    notional_usd = args.notional_usd or derived_notional_usd(
        size=args.size,
        close=signal.components.get("close"),
    )
    order_result = run_supervised_order(
        trial_id=trial_id,
        symbol=symbol,
        side=side,
        size=args.size,
        leverage=args.leverage,
        client_order_id=client_order_id,
        order_type=args.order_type,
        notional_usd=notional_usd,
        aura_root=args.aura_root,
        dry_run=dry_run,
        actor=args.actor,
    )
    return {
        "requested": True,
        "called": True,
        "dry_run": dry_run,
        "side": side,
        "client_order_id": client_order_id,
        "notional_usd": notional_usd,
        "result": order_result.to_dict(),
    }


def build_brain_signal_event(
    *,
    trial_id: str,
    actor: str,
    hypothesis_id: str,
    symbol: str,
    tf: str,
    candles: Sequence[Mapping[str, Any]],
    aura_root: str | Path | None,
    signal: IchimokuSignal,
    paper_summary: Mapping[str, Any],
) -> dict[str, Any]:
    latest_ts_ms = candles[-1].get("ts_ms") if candles else None
    return {
        "schema": BRAIN_SIGNAL_SCHEMA,
        "ts": utc_now_iso(),
        "trial_id": trial_id,
        "hypothesis_id": hypothesis_id,
        "actor": actor,
        "intent": "brain_signal",
        "symbol": symbol,
        "tf": tf,
        "inputs": {
            "market_path": str(ohlcv_path(symbol, tf, aura_root_override=aura_root)),
            "candle_count": len(candles),
            "latest_ts_ms": latest_ts_ms,
        },
        "signal": signal.to_dict(),
        "paper": dict(paper_summary),
        "human_auditable": True,
        "trace_ref": "runtime.tools.ichimoku_signal",
    }


def append_jsonl(path: Path, event: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True, separators=(",", ":")))
        handle.write("\n")
    return path


def default_trial_id(*, symbol: str, tf: str) -> str:
    safe_symbol = symbol.lower().replace("_", "-")
    return f"T-ichi-{safe_symbol}-{tf}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}"


def default_client_order_id(*, bias: str, symbol: str, ts_ms: int | None) -> str:
    safe_symbol = symbol.lower().replace("_", "-")
    suffix = str(ts_ms) if ts_ms is not None else datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"aura-ichi-{bias}-{safe_symbol}-{suffix}"


def derived_notional_usd(*, size: str, close: Any) -> str:
    try:
        notional = abs(Decimal(str(size)) * Decimal(str(close)))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("could not derive notional_usd from size and close") from exc
    return format(notional.quantize(Decimal("0.01")), "f")


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
