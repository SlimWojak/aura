"""CLI entrypoint for Track A synthetic-edge power controls."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
import json
from typing import Any, Sequence

from runtime.eval.power_test import (
    DEFAULT_ATR_PERIOD,
    DEFAULT_BLOCK_SIZE,
    DEFAULT_CSCV_GROUPS,
    DEFAULT_EDGE_SHARPE,
    DEFAULT_OOS_SPLIT,
    DEFAULT_TRIAL_COUNT,
    run_power_test_from_store,
)
from runtime.market import DEFAULT_SYMBOLS, DEFAULT_TFS


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = dispatch(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 1


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run paper-only Track A synthetic power controls.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--positive", action="store_true", help="inject a synthetic ATR edge")
    mode.add_argument("--negative", action="store_true", help="block-shuffle returns with no edge")
    parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOLS[0], help="Kraken futures symbol")
    parser.add_argument("--tf", default=DEFAULT_TFS[0], help="stored OHLCV timeframe")
    parser.add_argument("--fee-bps", type=float, default=4.0, help="recorded fee assumption for parity")
    parser.add_argument(
        "--oos-split",
        type=float,
        default=DEFAULT_OOS_SPLIT,
        help="chronological IS fraction; the OOS return segment is scored",
    )
    parser.add_argument(
        "--trial-count",
        type=int,
        default=DEFAULT_TRIAL_COUNT,
        help="honest tried-variant count used for DSR deflation",
    )
    parser.add_argument(
        "--atr-period",
        type=int,
        default=DEFAULT_ATR_PERIOD,
        help="Wilder ATR period used to normalize close-to-close returns",
    )
    parser.add_argument(
        "--cscv-groups",
        type=int,
        default=DEFAULT_CSCV_GROUPS,
        help="even number of chronological CSCV groups for PBO",
    )
    parser.add_argument(
        "--edge-sharpe",
        type=float,
        default=DEFAULT_EDGE_SHARPE,
        help="positive-control period Sharpe in ATR-normalized units",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=DEFAULT_BLOCK_SIZE,
        help="bars per block for negative-control block shuffling",
    )
    parser.add_argument("--regime-tf", help="accepted for thin-spine flag parity")
    parser.add_argument("--regime-htf", default="1d", help="accepted for thin-spine flag parity")
    parser.add_argument("--output-dir", help="write artifacts to an explicit directory")
    return parser


def dispatch(args: Namespace) -> dict[str, Any]:
    mode = "positive" if args.positive else "negative"
    return run_power_test_from_store(
        mode=mode,
        symbol=args.symbol,
        tf=args.tf,
        aura_root=args.aura_root,
        fee_bps=args.fee_bps,
        oos_split=args.oos_split,
        trial_count=args.trial_count,
        atr_period=args.atr_period,
        cscv_groups=args.cscv_groups,
        edge_sharpe=args.edge_sharpe,
        block_size=args.block_size,
        output_dir=args.output_dir,
        regime_tf=args.regime_tf,
        regime_htf=args.regime_htf,
    )


if __name__ == "__main__":
    raise SystemExit(main())
