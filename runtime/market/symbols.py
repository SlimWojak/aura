"""Kraken futures-paper market symbols for Aura."""

from __future__ import annotations

import re


DEFAULT_SYMBOLS = ("PF_XBTUSD",)
OPTIONAL_SYMBOLS = ("PF_ETHUSD",)
KNOWN_SYMBOLS = DEFAULT_SYMBOLS + OPTIONAL_SYMBOLS
DEFAULT_TFS = ("1h",)
SUPPORTED_TFS = ("1m", "5m", "15m", "30m", "1h", "4h", "1d")

SPOT_TO_FUTURES_SYMBOL = {
    "XBTUSD": "PF_XBTUSD",
    "ETHUSD": "PF_ETHUSD",
}
FUTURES_TO_SPOT_PAIR = {value: key for key, value in SPOT_TO_FUTURES_SYMBOL.items()}

_SYMBOL_RE = re.compile(r"^[A-Z0-9_]+$")


def validate_symbol(symbol: str) -> str:
    """Return a safe Kraken futures-paper symbol."""

    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol is required")
    if not normalized.startswith("PF_"):
        raise ValueError(f"symbol must be a Kraken futures paper symbol, got {symbol!r}")
    if _SYMBOL_RE.fullmatch(normalized) is None:
        raise ValueError(f"symbol contains unsupported characters: {symbol!r}")
    return normalized


def validate_tf(tf: str) -> str:
    """Return a supported Kraken Futures Charts resolution."""

    normalized = tf.strip().lower()
    if normalized not in SUPPORTED_TFS:
        allowed = ", ".join(SUPPORTED_TFS)
        raise ValueError(f"tf must be one of {allowed}; got {tf!r}")
    return normalized
