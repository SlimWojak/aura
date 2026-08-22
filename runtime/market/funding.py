"""Kraken Futures historical funding-rate ingest for Aura market data."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from runtime.market.ohlcv import market_root, meta_path, read_meta_file, utc_now_iso
from runtime.market.symbols import validate_symbol
from runtime.runner.supervised_paper import KrakenCommandError, resolve_kraken_bin, run_kraken_json


FUNDING_SCHEMA = "aura.funding_rate.v1"
FUNDING_SOURCE = "kraken_futures_historical_funding_rates"
HISTORICAL_FUNDING_COMMAND = ("futures", "historical-funding-rates")
FORBIDDEN_FUNDING_ARGS = {"--allow-dangerous", "paper", "buy", "sell", "cancel", "cancel-all", "live"}


def pull_funding(
    *,
    symbol: str,
    aura_root: str | Path | None = None,
    kraken_bin: str | Path | None = None,
) -> dict[str, Any]:
    """Pull public historical funding rates from Kraken CLI and merge JSONL."""

    safe_symbol = validate_symbol(symbol)
    kraken_path = resolve_kraken_bin(kraken_bin)
    args = (*HISTORICAL_FUNDING_COMMAND, safe_symbol, "-o", "json")
    validate_funding_command(args)
    payload = run_kraken_json(kraken_path, args)
    raw_rates = extract_funding_rows(payload)
    ingested_at = utc_now_iso()
    rates = [
        normalize_funding_rate(raw, symbol=safe_symbol, ingested_at=ingested_at)
        for raw in raw_rates
    ]
    result = merge_funding_rates(safe_symbol, rates, aura_root_override=aura_root)
    result["command"] = ["kraken", *args]
    return result


def validate_funding_command(args: Sequence[str]) -> None:
    if tuple(args[:2]) != HISTORICAL_FUNDING_COMMAND:
        raise ValueError("funding ingest only permits kraken futures historical-funding-rates")
    if "-o" not in args or "json" not in args:
        raise ValueError("funding ingest requires JSON output")
    forbidden = FORBIDDEN_FUNDING_ARGS.intersection(args)
    if forbidden:
        forbidden_text = ", ".join(sorted(forbidden))
        raise ValueError(f"funding ingest command contains forbidden argument(s): {forbidden_text}")


def funding_path(symbol: str, *, aura_root_override: str | Path | None = None) -> Path:
    safe_symbol = validate_symbol(symbol)
    return market_root(aura_root_override) / "funding" / f"{safe_symbol}.jsonl"


def normalize_funding_rate(
    raw: Mapping[str, Any],
    *,
    symbol: str,
    ingested_at: str,
) -> dict[str, Any]:
    safe_symbol = validate_symbol(symbol)
    ts = normalize_ts(extract_first(raw, ("ts", "timestamp", "time", "datetime", "date")))
    funding_rate = decimal_string(
        extract_first(raw, ("funding_rate", "fundingRate", "rate")),
        field_name="funding_rate",
    )
    relative_funding_rate = decimal_string(
        extract_first(
            raw,
            (
                "relative_funding_rate",
                "relativeFundingRate",
                "relative_rate",
                "relativeRate",
            ),
        ),
        field_name="relative_funding_rate",
    )
    return {
        "schema": FUNDING_SCHEMA,
        "symbol": safe_symbol,
        "ts": ts,
        "funding_rate": funding_rate,
        "relative_funding_rate": relative_funding_rate,
        "source": FUNDING_SOURCE,
        "ingested_at": ingested_at,
    }


def merge_funding_rates(
    symbol: str,
    rates: Iterable[Mapping[str, Any]],
    *,
    aura_root_override: str | Path | None = None,
) -> dict[str, Any]:
    path = funding_path(symbol, aura_root_override=aura_root_override)
    existing_by_ts = {str(rate["ts"]): rate for rate in read_funding_rates_from_path(path)}
    incoming_count = 0
    for rate in rates:
        ts = str(rate["ts"])
        existing_by_ts[ts] = dict(rate)
        incoming_count += 1

    merged = [existing_by_ts[ts] for ts in sorted(existing_by_ts)]
    write_funding_rates(path, merged)
    meta = write_funding_meta(symbol, merged, aura_root_override=aura_root_override)
    return {
        "symbol": validate_symbol(symbol),
        "path": str(path),
        "meta_path": str(meta_path(symbol, aura_root_override=aura_root_override)),
        "fetched_count": incoming_count,
        "stored_count": len(merged),
        "earliest_ts": merged[0]["ts"] if merged else None,
        "latest_ts": merged[-1]["ts"] if merged else None,
        "source": FUNDING_SOURCE,
        "meta": meta,
    }


def read_funding_rates(
    symbol: str,
    *,
    aura_root_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    return read_funding_rates_from_path(funding_path(symbol, aura_root_override=aura_root_override))


def read_last_funding_rates(
    symbol: str,
    *,
    tail: int,
    aura_root_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    if tail < 0:
        raise ValueError("tail must be non-negative")
    rates = read_funding_rates(symbol, aura_root_override=aura_root_override)
    return rates[-tail:] if tail else []


def funding_status(*, aura_root_override: str | Path | None = None) -> list[dict[str, Any]]:
    root = market_root(aura_root_override)
    funding_root = root / "funding"
    entries: list[dict[str, Any]] = []
    if not funding_root.exists():
        return entries
    for rate_path in sorted(funding_root.glob("*.jsonl")):
        symbol = validate_symbol(rate_path.stem)
        rates = read_funding_rates_from_path(rate_path)
        entries.append(
            {
                "symbol": symbol,
                "path": str(rate_path),
                "funding_count": len(rates),
                "earliest_ts": rates[0]["ts"] if rates else None,
                "latest_ts": rates[-1]["ts"] if rates else None,
            }
        )
    return entries


def read_funding_rates_from_path(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rates: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            rate = json.loads(stripped)
            validate_funding_rate(rate, path=path, line_number=line_number)
            rates.append(rate)
    return sorted(rates, key=lambda rate: str(rate["ts"]))


def write_funding_rates(path: Path, rates: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for rate in rates:
            handle.write(json.dumps(dict(rate), sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def write_funding_meta(
    symbol: str,
    rates: list[Mapping[str, Any]],
    *,
    aura_root_override: str | Path | None = None,
) -> dict[str, Any]:
    safe_symbol = validate_symbol(symbol)
    path = meta_path(safe_symbol, aura_root_override=aura_root_override)
    now = utc_now_iso()
    existing = read_meta_file(path)
    meta = dict(existing)
    meta["schema"] = str(existing.get("schema", "aura.market_meta.v1"))
    meta["symbol"] = safe_symbol
    meta["refreshed_at"] = now
    meta["funding"] = {
        "earliest_ts": rates[0]["ts"] if rates else None,
        "latest_ts": rates[-1]["ts"] if rates else None,
        "funding_count": len(rates),
        "source": FUNDING_SOURCE,
        "refreshed_at": now,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def extract_funding_rows(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return mapping_rows(payload)
    if not isinstance(payload, Mapping):
        raise ValueError("Kraken funding response must be a list or object")
    for key in (
        "rates",
        "funding_rates",
        "fundingRates",
        "historicalFundingRates",
        "data",
        "result",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return mapping_rows(value)
    raise ValueError("Kraken funding response missing rates list")


def mapping_rows(rows: list[Any]) -> list[Mapping[str, Any]]:
    mapped: list[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("Kraken funding row must be an object")
        mapped.append(row)
    return mapped


def validate_funding_rate(rate: Mapping[str, Any], *, path: Path, line_number: int) -> None:
    if rate.get("schema") != FUNDING_SCHEMA:
        raise ValueError(f"{path}:{line_number} invalid funding schema")
    validate_symbol(str(rate.get("symbol", "")))
    normalize_ts(rate.get("ts"))
    decimal_string(rate.get("funding_rate"), field_name="funding_rate")
    decimal_string(rate.get("relative_funding_rate"), field_name="relative_funding_rate")
    if rate.get("source") != FUNDING_SOURCE:
        raise ValueError(f"{path}:{line_number} invalid source")
    if not isinstance(rate.get("ingested_at"), str):
        raise ValueError(f"{path}:{line_number} invalid ingested_at")


def extract_first(raw: Mapping[str, Any], names: Sequence[str]) -> Any:
    for name in names:
        if name in raw:
            return raw[name]
    return None


def normalize_ts(raw_value: Any) -> str:
    if raw_value in (None, ""):
        raise ValueError("funding row missing ts")
    if isinstance(raw_value, (int, float)):
        return timestamp_to_iso(raw_value)
    raw_text = str(raw_value).strip()
    if not raw_text:
        raise ValueError("funding row missing ts")
    try:
        return timestamp_to_iso(Decimal(raw_text))
    except InvalidOperation:
        pass
    iso_text = raw_text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_text)
    except ValueError as exc:
        raise ValueError(f"funding row has invalid ts: {raw_value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def timestamp_to_iso(raw_value: int | float | Decimal) -> str:
    value = Decimal(str(raw_value))
    if not value.is_finite():
        raise ValueError("funding row has non-finite ts")
    seconds = value
    if abs(seconds) > Decimal("100000000000"):
        seconds = seconds / Decimal("1000")
    parsed = datetime.fromtimestamp(float(seconds), tz=UTC)
    return parsed.isoformat().replace("+00:00", "Z")


def decimal_string(raw_value: Any, *, field_name: str) -> str:
    if raw_value in (None, ""):
        raise ValueError(f"funding row missing {field_name}")
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"funding row has invalid {field_name}") from exc
    if not value.is_finite():
        raise ValueError(f"funding row has non-finite {field_name}")
    return format(value, "f")


__all__ = [
    "FUNDING_SCHEMA",
    "FUNDING_SOURCE",
    "KrakenCommandError",
    "funding_path",
    "funding_status",
    "merge_funding_rates",
    "normalize_funding_rate",
    "pull_funding",
    "read_funding_rates",
    "read_last_funding_rates",
    "validate_funding_command",
]
