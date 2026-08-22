"""Pure paper risk admission checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from runtime.risk.policy import DEFAULT_POLICY, RiskPolicy


REQUIRED_PROPOSAL_FIELDS = (
    "symbol",
    "side",
    "size",
    "order_type",
    "leverage",
    "client_order_id",
)
REQUIRED_ACCOUNT_STATE_FIELDS = (
    "equity",
    "open_positions_count",
    "daily_pnl",
    "weekly_pnl",
    "kill_state",
)
STATE_TS_FIELDS = ("as_of", "observed_at", "state_ts", "ts")
PAPER_KILL_STATES = ("armed", "soft", "hard")


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """Result of applying the policy gate to one proposed paper order."""

    allowed: bool
    reasons: tuple[str, ...]
    policy_version: str
    evaluated_at: str

    @property
    def result(self) -> str:
        return "allow" if self.allowed else "reject"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "policy_version": self.policy_version,
            "evaluated_at": self.evaluated_at,
        }


def admit(
    proposal: Mapping[str, Any],
    account_state: Mapping[str, Any],
    policy: RiskPolicy = DEFAULT_POLICY,
    *,
    now: datetime | None = None,
) -> AdmissionResult:
    """Admit or reject a paper order proposal.

    This function has no side effects, calls no LLMs, and touches no venue APIs.
    Missing or stale account state rejects because later runner code must not
    infer safety from absent state.
    """

    evaluated_at = _now(now)
    reasons: list[str] = []

    if not policy.is_paper_only:
        reasons.append("policy mode is not paper_only")

    _require_fields("proposal", proposal, REQUIRED_PROPOSAL_FIELDS, reasons)
    _require_fields("account_state", account_state, REQUIRED_ACCOUNT_STATE_FIELDS, reasons)

    state_ts = _state_timestamp(account_state)
    if state_ts is None:
        reasons.append("account_state timestamp missing")
    elif state_ts > evaluated_at:
        reasons.append("account_state timestamp is in the future")
    elif (evaluated_at - state_ts).total_seconds() > policy.dead_man_seconds:
        reasons.append("account_state stale")

    kill_state = account_state.get("kill_state")
    if kill_state not in PAPER_KILL_STATES:
        reasons.append("account_state kill_state invalid")
    elif kill_state in ("soft", "hard"):
        reasons.append(f"kill_state {kill_state}")

    notional_usd = _proposal_notional_usd(proposal)
    if notional_usd is None:
        reasons.append("proposal notional_usd missing or invalid")
    elif notional_usd > Decimal(str(policy.max_notional_usd)):
        reasons.append("proposal notional_usd exceeds max_notional_usd")

    leverage = _decimal_value(proposal.get("leverage"))
    if leverage is None:
        reasons.append("proposal leverage missing or invalid")
    elif leverage > Decimal(str(policy.max_leverage)):
        reasons.append("proposal leverage exceeds max_leverage")

    open_positions_count = _int_value(account_state.get("open_positions_count"))
    if open_positions_count is None:
        reasons.append("account_state open_positions_count missing or invalid")
    elif open_positions_count >= policy.max_open_positions:
        reasons.append("account_state open_positions_count at or above max_open_positions")

    daily_pnl = _decimal_value(account_state.get("daily_pnl"))
    if daily_pnl is None:
        reasons.append("account_state daily_pnl missing or invalid")
    elif daily_pnl <= -Decimal(str(policy.max_daily_loss_usd)):
        reasons.append("account_state daily_pnl breaches max_daily_loss_usd")

    weekly_pnl = _decimal_value(account_state.get("weekly_pnl"))
    if weekly_pnl is None:
        reasons.append("account_state weekly_pnl missing or invalid")
    elif weekly_pnl <= -Decimal(str(policy.max_weekly_loss_usd)):
        reasons.append("account_state weekly_pnl breaches max_weekly_loss_usd")

    equity = _decimal_value(account_state.get("equity"))
    if equity is None:
        reasons.append("account_state equity missing or invalid")
    elif equity <= Decimal("0"):
        reasons.append("account_state equity must be positive")

    return AdmissionResult(
        allowed=not reasons,
        reasons=tuple(reasons),
        policy_version=policy.policy_version,
        evaluated_at=evaluated_at.isoformat().replace("+00:00", "Z"),
    )


def _now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(tz=UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _require_fields(
    label: str,
    values: Mapping[str, Any],
    field_names: tuple[str, ...],
    reasons: list[str],
) -> None:
    for field_name in field_names:
        if field_name not in values or values[field_name] in (None, ""):
            reasons.append(f"{label} {field_name} missing")


def _state_timestamp(account_state: Mapping[str, Any]) -> datetime | None:
    for field_name in STATE_TS_FIELDS:
        raw_value = account_state.get(field_name)
        if raw_value not in (None, ""):
            return _datetime_value(raw_value)
    return None


def _datetime_value(raw_value: Any) -> datetime | None:
    if isinstance(raw_value, datetime):
        value = raw_value
    elif isinstance(raw_value, int | float):
        value = datetime.fromtimestamp(raw_value, tz=UTC)
    elif isinstance(raw_value, str):
        normalized = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
        try:
            value = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _proposal_notional_usd(proposal: Mapping[str, Any]) -> Decimal | None:
    explicit_notional = _decimal_value(proposal.get("notional_usd"))
    if explicit_notional is not None:
        return explicit_notional

    size = _decimal_value(proposal.get("size"))
    price = _decimal_value(proposal.get("price_usd"))
    if size is None or price is None:
        return None
    return abs(size * price)


def _decimal_value(raw_value: Any) -> Decimal | None:
    if raw_value in (None, ""):
        return None
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite():
        return None
    return value


def _int_value(raw_value: Any) -> int | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, bool):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None

