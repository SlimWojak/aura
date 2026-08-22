"""CLI for Aura Phase 1 regime labels.

This tool is paper-only evidence plumbing. It labels stored market candles and
does not call Kraken private APIs, propose orders, or wire into cartridge eval.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from runtime.market import DEFAULT_SYMBOLS, ohlcv_path, read_candles, validate_symbol, validate_tf
from runtime.market.ohlcv import aura_root
from runtime.regime import REGIME_SUMMARY_SCHEMA, RegimeParams, classify_series, resample_1h_candles
from runtime.regime.types import RegimeSnapshot


DEFAULT_TF = "4h"
DEFAULT_HTF = "1d"


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
    parser = ArgumentParser(description="Label Aura Ichimoku regimes from stored 1h OHLCV JSONL.")
    subparsers = parser.add_subparsers(dest="command")

    label_parser = subparsers.add_parser("label", help="write regime labels and occupancy summary")
    label_parser.add_argument("--symbol", default=DEFAULT_SYMBOLS[0], help="Kraken futures-paper symbol")
    label_parser.add_argument("--tf", default=DEFAULT_TF, help="regime timeframe resampled from 1h")
    label_parser.add_argument(
        "--htf",
        default=DEFAULT_HTF,
        help="optional higher-timeframe veto resampled from 1h; use 'none' to disable",
    )
    label_parser.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")

    return parser


def dispatch(args: Namespace) -> dict[str, Any]:
    match args.command:
        case "label":
            return command_label(args)
        case _:
            raise ValueError(f"unknown command: {args.command}")


def command_label(args: Namespace) -> dict[str, Any]:
    symbol = validate_symbol(args.symbol)
    tf = validate_tf(args.tf)
    htf = _optional_tf(args.htf)
    root = aura_root(args.aura_root)
    source_candles = read_candles(symbol, "1h", aura_root_override=root)
    if not source_candles:
        raise ValueError(f"no stored 1h candles found at {ohlcv_path(symbol, '1h', aura_root_override=root)}")

    params = RegimeParams(regime_tf=tf, htf_tf=htf)
    candles = resample_1h_candles(source_candles, symbol=symbol, target_tf=tf)
    if not candles:
        raise ValueError(f"no complete {tf} candles could be resampled from stored 1h data")
    htf_candles = (
        resample_1h_candles(source_candles, symbol=symbol, target_tf=htf) if htf is not None else None
    )
    snapshots = classify_series(candles, params=params, tf=tf, htf_candles=htf_candles)
    regime_id = default_regime_id(symbol=symbol, tf=tf)
    output_dir = root / "evidence" / "regimes" / regime_id
    labels_path = write_labels(output_dir / "labels.jsonl", snapshots=snapshots, symbol=symbol)
    summary = build_summary(
        regime_id=regime_id,
        symbol=symbol,
        tf=tf,
        htf=htf,
        source_candle_count=len(source_candles),
        candle_count=len(candles),
        snapshots=snapshots,
        params=params,
        labels_path=labels_path,
    )
    summary_path = write_json(output_dir / "summary.json", summary)
    return {
        "ok": True,
        "regime_id": regime_id,
        "symbol": symbol,
        "tf": tf,
        "htf": htf,
        "outputs": {
            "labels_jsonl": str(labels_path),
            "summary_json": str(summary_path),
        },
        "summary": {
            "occupancy_pct": summary["occupancy_pct"],
            "flip_rate": summary["flip_rate"],
            "state_count": summary["state_count"],
        },
    }


def build_summary(
    *,
    regime_id: str,
    symbol: str,
    tf: str,
    htf: str | None,
    source_candle_count: int,
    candle_count: int,
    snapshots: Sequence[RegimeSnapshot],
    params: RegimeParams,
    labels_path: Path,
) -> dict[str, Any]:
    states = [snapshot.state.value for snapshot in snapshots]
    counts = Counter(states)
    total = len(states)
    flips = sum(1 for index in range(1, total) if states[index] != states[index - 1])
    occupancy_pct = {
        state: round((counts.get(state, 0) / total) * 100.0, 4) if total else 0.0
        for state in ("TREND_BULL", "TREND_BEAR", "TRANSITION", "RANGE", "VOLATILE")
    }
    return {
        "schema": REGIME_SUMMARY_SCHEMA,
        "regime_id": regime_id,
        "generated_at": utc_now_iso(),
        "symbol": symbol,
        "tf": tf,
        "htf": htf,
        "source": {
            "stored_tf": "1h",
            "stored_1h_candles": source_candle_count,
            "resampled_candles": candle_count,
        },
        "params": params.to_dict(),
        "state_count": {
            state: counts.get(state, 0)
            for state in ("TREND_BULL", "TREND_BEAR", "TRANSITION", "RANGE", "VOLATILE")
        },
        "occupancy_pct": occupancy_pct,
        "flip_count": flips,
        "flip_rate": round(flips / (total - 1), 10) if total > 1 else 0.0,
        "labels_jsonl": str(labels_path),
        "fitness_note": "Phase 1 scores label stability, occupancy, and flip rate; no PnL claim.",
    }


def write_labels(
    path: Path,
    *,
    snapshots: Sequence[RegimeSnapshot],
    symbol: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for snapshot in snapshots:
            payload = snapshot.to_dict()
            payload["symbol"] = symbol
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    return path


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def default_regime_id(*, symbol: str, tf: str) -> str:
    safe_symbol = symbol.lower().replace("_", "-")
    return f"R-regime-{safe_symbol}-{tf}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}"


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _optional_tf(value: str | None) -> str | None:
    if value is None or value.strip().lower() in {"", "none", "off", "false"}:
        return None
    return validate_tf(value)


if __name__ == "__main__":
    raise SystemExit(main())
