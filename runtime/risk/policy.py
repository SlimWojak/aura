"""Paper risk policy defaults and config loading."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping
import tomllib


POLICY_VERSION = "risk-2026-08-22"
PAPER_ONLY_MODE = "paper_only"


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Locked paper-phase risk ceilings from RISK_POLICY.md."""

    max_notional_usd: float = 500.0
    max_open_positions: int = 2
    max_daily_loss_usd: float = 200.0
    max_weekly_loss_usd: float = 500.0
    max_leverage: float = 2.0
    dead_man_seconds: int = 600
    mode: str = PAPER_ONLY_MODE
    policy_version: str = POLICY_VERSION

    @property
    def is_paper_only(self) -> bool:
        return self.mode == PAPER_ONLY_MODE


DEFAULT_POLICY = RiskPolicy()


def from_mapping(values: Mapping[str, Any]) -> RiskPolicy:
    """Build a policy from a mapping, falling back to locked defaults."""

    policy = DEFAULT_POLICY
    replacements: dict[str, Any] = {}

    for field_name in (
        "max_notional_usd",
        "max_open_positions",
        "max_daily_loss_usd",
        "max_weekly_loss_usd",
        "max_leverage",
        "dead_man_seconds",
        "mode",
        "policy_version",
    ):
        if field_name in values:
            replacements[field_name] = values[field_name]

    if replacements:
        policy = replace(policy, **replacements)
    return policy


def load_policy(config_path: str | Path | None = None) -> RiskPolicy:
    """Load paper risk policy from TOML, or return locked defaults.

    The example config mirrors RISK_POLICY.md. Runtime callers may pass a copied
    config outside git; missing files are not silently ignored because risk must
    fail closed at the caller boundary.
    """

    if config_path is None:
        return DEFAULT_POLICY

    path = Path(config_path)
    with path.open("rb") as handle:
        config = tomllib.load(handle)

    risk_values = dict(config.get("risk", {}))
    if "mode" in config and "mode" not in risk_values:
        risk_values["mode"] = config["mode"]
    return from_mapping(risk_values)

