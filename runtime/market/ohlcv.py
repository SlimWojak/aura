"""JSONL storage helpers for Kraken Futures OHLCV candles."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime.market.symbols import validate_symbol, validate_tf


CANDLE_SCHEMA = "aura.ohlcv_candle.v1"
META_SCHEMA = "aura.ohlcv_meta.v1"
SOURCE = "kraken_futures_charts"
DEFAULT_AURA_ROOT = Path("/var/aura")

_PRICE_FIELDS = ("open", "high", "low", "close")


def aura_root(aura_root_override: str | Path | None = None) -> Path:
    if aura_root_override is not None:
        return Path(aura_root_override)
    return Path(os.environ.get("AURA_ROOT", str(DEFAULT_AURA_ROOT)))


def market_root(aura_root_override: str | Path | None = None) -> Path:
    return aura_root(aura_root_override) / "market"


def ohlcv_path(
    symbol: str,
    tf: str,
    *,
    aura_root_override: str | Path | None = None,
) -> Path:
    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    return market_root(aura_root_override) / "ohlcv" / safe_symbol / f"{safe_tf}.jsonl"


def meta_path(symbol: str, *, aura_root_override: str | Path | None = None) -> Path:
    safe_symbol = validate_symbol(symbol)
    return market_root(aura_root_override) / "meta" / f"{safe_symbol}.json"


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def normalize_candle(
    raw: Mapping[str, Any],
    *,
    symbol: str,
    tf: str,
    ingested_at: str,
) -> dict[str, Any]:
    """Normalize one Kraken Futures Charts candle for Aura JSONL."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    ts_ms = integer_value(raw.get("time"))
    if ts_ms is None:
        raise ValueError("candle missing integer millisecond time")

    candle: dict[str, Any] = {
        "schema": CANDLE_SCHEMA,
        "symbol": safe_symbol,
        "tf": safe_tf,
        "ts_ms": ts_ms,
        "source": SOURCE,
        "ingested_at": ingested_at,
    }
    for field_name in _PRICE_FIELDS:
        candle[field_name] = decimal_string(raw.get(field_name), field_name=field_name)
    candle["volume"] = decimal_string(raw.get("volume"), field_name="volume")
    return candle


def merge_candles(
    symbol: str,
    tf: str,
    candles: Iterable[Mapping[str, Any]],
    *,
    aura_root_override: str | Path | None = None,
    backfill_pages: int = 0,
) -> dict[str, Any]:
    """Idempotently upsert candles by ``ts_ms`` and rewrite sorted JSONL."""

    path = ohlcv_path(symbol, tf, aura_root_override=aura_root_override)
    existing_by_ts = {int(candle["ts_ms"]): candle for candle in read_candles_from_path(path)}
    incoming_count = 0
    for candle in candles:
        ts_ms = int(candle["ts_ms"])
        existing_by_ts[ts_ms] = dict(candle)
        incoming_count += 1

    merged = [existing_by_ts[ts_ms] for ts_ms in sorted(existing_by_ts)]
    write_candles(path, merged)
    meta = write_meta(
        symbol,
        tf,
        merged,
        aura_root_override=aura_root_override,
        backfill_pages=backfill_pages,
    )
    return {
        "symbol": validate_symbol(symbol),
        "tf": validate_tf(tf),
        "path": str(path),
        "meta_path": str(meta_path(symbol, aura_root_override=aura_root_override)),
        "fetched_count": incoming_count,
        "stored_count": len(merged),
        "earliest_ts_ms": merged[0]["ts_ms"] if merged else None,
        "latest_ts_ms": merged[-1]["ts_ms"] if merged else None,
        "source": SOURCE,
        "meta": meta,
    }


def read_candles(
    symbol: str,
    tf: str,
    *,
    aura_root_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    return read_candles_from_path(ohlcv_path(symbol, tf, aura_root_override=aura_root_override))


def read_last_candles(
    symbol: str,
    tf: str,
    *,
    tail: int,
    aura_root_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    if tail < 0:
        raise ValueError("tail must be non-negative")
    candles = read_candles(symbol, tf, aura_root_override=aura_root_override)
    return candles[-tail:] if tail else []


def read_latest_ts_ms(
    symbol: str,
    tf: str,
    *,
    aura_root_override: str | Path | None = None,
) -> int | None:
    candles = read_candles(symbol, tf, aura_root_override=aura_root_override)
    if not candles:
        return None
    return int(candles[-1]["ts_ms"])


def read_earliest_ts_ms(
    symbol: str,
    tf: str,
    *,
    aura_root_override: str | Path | None = None,
) -> int | None:
    candles = read_candles(symbol, tf, aura_root_override=aura_root_override)
    if not candles:
        return None
    return int(candles[0]["ts_ms"])


def status(*, aura_root_override: str | Path | None = None) -> dict[str, Any]:
    root = market_root(aura_root_override)
    ohlcv_root = root / "ohlcv"
    entries: list[dict[str, Any]] = []
    if ohlcv_root.exists():
        for symbol_dir in sorted(path for path in ohlcv_root.iterdir() if path.is_dir()):
            symbol = validate_symbol(symbol_dir.name)
            for candle_path in sorted(symbol_dir.glob("*.jsonl")):
                tf = validate_tf(candle_path.stem)
                candles = read_candles_from_path(candle_path)
                entries.append(
                    {
                        "symbol": symbol,
                        "tf": tf,
                        "path": str(candle_path),
                        "candle_count": len(candles),
                        "earliest_ts_ms": candles[0]["ts_ms"] if candles else None,
                        "latest_ts_ms": candles[-1]["ts_ms"] if candles else None,
                    }
                )

    return {
        "ok": True,
        "market_root": str(root),
        "entries": entries,
        "meta": read_all_meta(root / "meta"),
    }


def read_candles_from_path(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    candles: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            candle = json.loads(stripped)
            validate_candle(candle, path=path, line_number=line_number)
            candles.append(candle)
    return sorted(candles, key=lambda candle: int(candle["ts_ms"]))


def write_candles(path: Path, candles: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for candle in candles:
            handle.write(json.dumps(dict(candle), sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def write_meta(
    symbol: str,
    tf: str,
    candles: list[Mapping[str, Any]],
    *,
    aura_root_override: str | Path | None = None,
    backfill_pages: int = 0,
) -> dict[str, Any]:
    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    path = meta_path(safe_symbol, aura_root_override=aura_root_override)
    now = utc_now_iso()
    existing = read_meta_file(path)
    tfs = dict(existing.get("tfs", {})) if isinstance(existing.get("tfs"), Mapping) else {}
    funding = existing.get("funding") if isinstance(existing.get("funding"), Mapping) else None
    previous_tf = tfs.get(safe_tf) if isinstance(tfs.get(safe_tf), Mapping) else {}
    previous_backfill_pages = integer_value(previous_tf.get("backfill_pages"))
    if previous_backfill_pages is None:
        previous_backfill_pages = 0
    total_backfill_pages = previous_backfill_pages + backfill_pages
    earliest_ts_ms = int(candles[0]["ts_ms"]) if candles else None
    latest_ts_ms = int(candles[-1]["ts_ms"]) if candles else None
    tfs[safe_tf] = {
        "earliest_ts_ms": earliest_ts_ms,
        "latest_ts_ms": latest_ts_ms,
        "last_ts_ms": latest_ts_ms,
        "candle_count": len(candles),
        "backfill_pages": total_backfill_pages,
        "source": SOURCE,
        "refreshed_at": now,
    }
    meta = {
        "schema": META_SCHEMA,
        "symbol": safe_symbol,
        "tf": safe_tf,
        "earliest_ts_ms": earliest_ts_ms,
        "latest_ts_ms": latest_ts_ms,
        "last_ts_ms": latest_ts_ms,
        "candle_count": len(candles),
        "backfill_pages": total_backfill_pages,
        "source": SOURCE,
        "refreshed_at": now,
        "tfs": tfs,
    }
    if funding is not None:
        meta["funding"] = dict(funding)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def read_meta_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"metadata must be an object: {path}")
    return payload


def read_all_meta(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if not path.exists():
        return payload
    for meta_file in sorted(path.glob("*.json")):
        payload[meta_file.stem] = read_meta_file(meta_file)
    return payload


def validate_candle(candle: Mapping[str, Any], *, path: Path, line_number: int) -> None:
    if candle.get("schema") != CANDLE_SCHEMA:
        raise ValueError(f"{path}:{line_number} invalid candle schema")
    validate_symbol(str(candle.get("symbol", "")))
    validate_tf(str(candle.get("tf", "")))
    if integer_value(candle.get("ts_ms")) is None:
        raise ValueError(f"{path}:{line_number} invalid ts_ms")
    for field_name in (*_PRICE_FIELDS, "volume"):
        decimal_string(candle.get(field_name), field_name=field_name)
    if candle.get("source") != SOURCE:
        raise ValueError(f"{path}:{line_number} invalid source")
    if not isinstance(candle.get("ingested_at"), str):
        raise ValueError(f"{path}:{line_number} invalid ingested_at")


def integer_value(raw_value: Any) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def decimal_string(raw_value: Any, *, field_name: str) -> str:
    if raw_value in (None, ""):
        raise ValueError(f"candle missing {field_name}")
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"candle has invalid {field_name}") from exc
    if not value.is_finite():
        raise ValueError(f"candle has non-finite {field_name}")
    return format(value, "f")
