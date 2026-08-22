"""Kraken Futures Charts REST ingest for Aura OHLCV."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from runtime.market.ohlcv import (
    SOURCE,
    merge_candles,
    normalize_candle,
    read_candles,
    read_earliest_ts_ms,
    read_latest_ts_ms,
    utc_now_iso,
)
from runtime.market.symbols import validate_symbol, validate_tf


CHARTS_BASE_URL = "https://futures.kraken.com/api/charts/v1/trade"
DEFAULT_COUNT = 720
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_BACKFILL_PAGES = 200
USER_AGENT = "aura-market-spine/1"


@dataclass(frozen=True, slots=True)
class ChartsHTTPError(RuntimeError):
    """Raised when Kraken Futures Charts cannot produce usable JSON."""

    url: str
    reason: str

    def __str__(self) -> str:
        return f"{self.url} failed: {self.reason}"


def pull_ohlcv(
    *,
    symbol: str,
    tf: str,
    aura_root: str | Path | None = None,
    count: int = DEFAULT_COUNT,
    from_ts: int | None = None,
    to_ts: int | None = None,
    backfill: bool = False,
    pages: int | None = None,
    since_ts_ms: int | None = None,
    max_pages: int = DEFAULT_MAX_BACKFILL_PAGES,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Fetch Kraken Futures Charts candles and merge them into Aura JSONL."""

    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    if count <= 0:
        raise ValueError("count must be positive")
    if pages is not None and pages <= 0:
        raise ValueError("pages must be positive")
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if since_ts_ms is not None and since_ts_ms <= 0:
        raise ValueError("since_ts_ms must be a positive unix millisecond timestamp")

    if backfill or pages is not None or since_ts_ms is not None:
        return pull_ohlcv_backfill(
            symbol=safe_symbol,
            tf=safe_tf,
            aura_root=aura_root,
            count=count,
            from_ts=from_ts,
            to_ts=to_ts,
            pages=pages,
            since_ts_ms=since_ts_ms,
            max_pages=max_pages,
            timeout_seconds=timeout_seconds,
        )

    latest_ts_ms = read_latest_ts_ms(safe_symbol, safe_tf, aura_root_override=aura_root)
    effective_from = from_ts
    if effective_from is None and latest_ts_ms is not None:
        effective_from = latest_ts_ms // 1000

    payload = fetch_charts(
        symbol=safe_symbol,
        tf=safe_tf,
        count=count,
        from_ts=effective_from,
        to_ts=to_ts,
        timeout_seconds=timeout_seconds,
    )
    raw_candles = extract_candles(payload)
    ingested_at = utc_now_iso()
    candles = [
        normalize_candle(raw, symbol=safe_symbol, tf=safe_tf, ingested_at=ingested_at)
        for raw in raw_candles
    ]
    result = merge_candles(safe_symbol, safe_tf, candles, aura_root_override=aura_root)
    result["url"] = build_charts_url(
        symbol=safe_symbol,
        tf=safe_tf,
        count=count,
        from_ts=effective_from,
        to_ts=to_ts,
    )
    result["previous_latest_ts_ms"] = latest_ts_ms
    result["backfill_pages"] = 0
    return result


def pull_ohlcv_backfill(
    *,
    symbol: str,
    tf: str,
    aura_root: str | Path | None,
    count: int,
    from_ts: int | None,
    to_ts: int | None,
    pages: int | None,
    since_ts_ms: int | None,
    max_pages: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    page_limit = min(pages if pages is not None else max_pages, max_pages)
    existing = read_candles(symbol, tf, aura_root_override=aura_root)
    seen_ts = {int(candle["ts_ms"]) for candle in existing}
    previous_earliest_ts_ms = read_earliest_ts_ms(symbol, tf, aura_root_override=aura_root)
    previous_latest_ts_ms = read_latest_ts_ms(symbol, tf, aura_root_override=aura_root)
    next_to_ts = to_ts
    if next_to_ts is None and previous_earliest_ts_ms is not None:
        next_to_ts = previous_earliest_ts_ms // 1000

    ingested_at = utc_now_iso()
    fetched_pages = 0
    fetched_count = 0
    normalized_candles: list[dict[str, Any]] = []
    urls: list[str] = []
    stop_reason = "page_limit"

    for _ in range(page_limit):
        url = build_charts_url(
            symbol=symbol,
            tf=tf,
            count=count,
            from_ts=from_ts,
            to_ts=next_to_ts,
        )
        payload = fetch_charts(
            symbol=symbol,
            tf=tf,
            count=count,
            from_ts=from_ts,
            to_ts=next_to_ts,
            timeout_seconds=timeout_seconds,
        )
        raw_candles = extract_candles(payload)
        if not raw_candles:
            stop_reason = "empty_page"
            break

        page_candles = [
            normalize_candle(raw, symbol=symbol, tf=tf, ingested_at=ingested_at)
            for raw in raw_candles
        ]
        page_ts = {int(candle["ts_ms"]) for candle in page_candles}
        filtered_page_candles = page_candles
        if since_ts_ms is not None:
            filtered_page_candles = [
                candle for candle in page_candles if int(candle["ts_ms"]) >= since_ts_ms
            ]

        new_ts = {int(candle["ts_ms"]) for candle in filtered_page_candles} - seen_ts
        if not new_ts:
            stop_reason = "since_reached" if since_ts_ms is not None and min(page_ts) <= since_ts_ms else "duplicate_page"
            break

        normalized_candles.extend(
            candle for candle in filtered_page_candles if int(candle["ts_ms"]) in new_ts
        )
        seen_ts.update(page_ts)
        fetched_count += len(page_candles)
        fetched_pages += 1
        urls.append(url)

        oldest_page_ts_ms = min(page_ts)
        if since_ts_ms is not None and oldest_page_ts_ms <= since_ts_ms:
            stop_reason = "since_reached"
            break

        oldest_page_ts = oldest_page_ts_ms // 1000
        if next_to_ts is not None and oldest_page_ts >= next_to_ts:
            stop_reason = "duplicate_page"
            break
        next_to_ts = oldest_page_ts

    result = merge_candles(
        symbol,
        tf,
        normalized_candles,
        aura_root_override=aura_root,
        backfill_pages=fetched_pages,
    )
    result["fetched_count"] = fetched_count
    result["backfill_pages"] = fetched_pages
    result["requested_pages"] = page_limit
    result["stop_reason"] = stop_reason
    result["urls"] = urls
    result["url"] = urls[-1] if urls else None
    result["previous_earliest_ts_ms"] = previous_earliest_ts_ms
    result["previous_latest_ts_ms"] = previous_latest_ts_ms
    result["since_ts_ms"] = since_ts_ms
    return result


def fetch_charts(
    *,
    symbol: str,
    tf: str,
    count: int,
    from_ts: int | None,
    to_ts: int | None,
    timeout_seconds: int,
) -> Mapping[str, Any]:
    url = build_charts_url(symbol=symbol, tf=tf, count=count, from_ts=from_ts, to_ts=to_ts)
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ChartsHTTPError(url, f"HTTP {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise ChartsHTTPError(url, str(exc.reason)) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ChartsHTTPError(url, f"invalid JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ChartsHTTPError(url, "response JSON must be an object")
    return payload


def build_charts_url(
    *,
    symbol: str,
    tf: str,
    count: int,
    from_ts: int | None,
    to_ts: int | None,
) -> str:
    safe_symbol = validate_symbol(symbol)
    safe_tf = validate_tf(tf)
    query: dict[str, str] = {"count": str(count)}
    if from_ts is not None:
        query["from"] = str(int(from_ts))
    if to_ts is not None:
        query["to"] = str(int(to_ts))
    return f"{CHARTS_BASE_URL}/{safe_symbol}/{safe_tf}?{urlencode(query)}"


def extract_candles(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_candles = payload.get("candles")
    if not isinstance(raw_candles, list):
        raise ValueError("Kraken Futures Charts response missing candles list")
    candles: list[Mapping[str, Any]] = []
    for raw in raw_candles:
        if not isinstance(raw, Mapping):
            raise ValueError("Kraken Futures Charts candle must be an object")
        candles.append(raw)
    return candles


def source_summary() -> dict[str, str]:
    return {
        "source": SOURCE,
        "url": CHARTS_BASE_URL,
        "method": "GET",
    }
