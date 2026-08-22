"""Hard regime permissioning for paper-only entry gates."""

from __future__ import annotations

from typing import Any

from runtime.regime.types import RegimeState


ENTRY_SIDES = {"long", "short"}


def regime_allows(side: str | None, state: RegimeState | str | None) -> tuple[bool, list[str]]:
    """Return whether a new entry side is allowed by a regime state.

    Exits are intentionally out of scope for this hard veto. Callers should apply
    this function only when opening or reversing into a new paper position.
    """

    normalized_side = _normalize_side(side)
    if normalized_side is None:
        return False, ["regime_veto", f"side_unknown:{side}"]

    normalized_state = _normalize_state(state)
    if normalized_state is None:
        reason = "regime_missing" if state in (None, "") else f"regime_unknown:{state}"
        return False, ["regime_veto", reason]

    if normalized_state == RegimeState.TREND_BULL and normalized_side == "long":
        return True, ["regime_allows", "TREND_BULL_allows_long"]
    if normalized_state == RegimeState.TREND_BEAR and normalized_side == "short":
        return True, ["regime_allows", "TREND_BEAR_allows_short"]

    return False, ["regime_veto", f"{normalized_state.value}_denies_{normalized_side}_entry"]


def _normalize_side(side: str | None) -> str | None:
    if side is None:
        return None
    normalized = side.strip().lower()
    if normalized in ENTRY_SIDES:
        return normalized
    return None


def _normalize_state(state: RegimeState | str | None) -> RegimeState | None:
    if isinstance(state, RegimeState):
        return state
    if state is None:
        return None
    try:
        return RegimeState(str(state).strip())
    except ValueError:
        return None
