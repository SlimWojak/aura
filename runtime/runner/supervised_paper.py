"""Thin supervised futures-paper runner.

This module is intentionally human-triggered only. It reads Kraken futures
paper state, calls the pure risk gate, writes decision JSONL, and only then
invokes the futures paper order command for allowed non-dry-run requests.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping, Sequence

from runtime.evidence import append_decision_event, build_decision_event, decision_jsonl_path
from runtime.risk import AdmissionResult, admit


DEFAULT_SYMBOL = "PF_XBTUSD"
DEFAULT_SIZE = "0.001"
DEFAULT_ORDER_TYPE = "market"
DEFAULT_LEVERAGE = "1"
DEFAULT_ACTOR = "cos:supervised_paper"


@dataclass(frozen=True, slots=True)
class SupervisedOrderResult:
    """Result returned by the human-triggered supervised paper runner."""

    admission: AdmissionResult
    decision_path: Path
    event: Mapping[str, Any]
    account_state: Mapping[str, Any]
    order_called: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "admission": self.admission.to_dict(),
            "decision_jsonl": str(self.decision_path),
            "order_called": self.order_called,
            "account_state": dict(self.account_state),
            "event": dict(self.event),
        }


@dataclass(frozen=True, slots=True)
class KrakenCommandError(RuntimeError):
    """Raised when a Kraken CLI command cannot produce usable JSON."""

    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str

    def __str__(self) -> str:
        command_text = " ".join(self.command)
        if self.returncode is None:
            return f"{command_text} did not produce valid JSON: {self.stderr}"
        return f"{command_text} failed with exit code {self.returncode}: {self.stderr}"


def run_supervised_order(
    *,
    trial_id: str,
    symbol: str = DEFAULT_SYMBOL,
    side: str = "buy",
    size: str = DEFAULT_SIZE,
    leverage: str = DEFAULT_LEVERAGE,
    client_order_id: str,
    order_type: str = DEFAULT_ORDER_TYPE,
    notional_usd: str | None = None,
    aura_root: str | Path | None = None,
    dry_run: bool = False,
    actor: str = DEFAULT_ACTOR,
    kraken_bin: str | Path | None = None,
) -> SupervisedOrderResult:
    """Run one supervised paper order attempt.

    Rejects and dry-runs never call the venue order command, but both append a
    decision event. Missing account-state fields or missing notional/price fail
    closed through ``runtime.risk.admit``.
    """

    now = datetime.now(tz=UTC)
    kraken_path = resolve_kraken_bin(kraken_bin)
    account_payload = read_paper_account_state(
        aura_root=aura_root,
        kraken_bin=kraken_path,
        observed_at=now,
    )
    account_state = account_payload["account_state"]
    proposal = build_proposal(
        symbol=symbol,
        side=side,
        size=size,
        order_type=order_type,
        leverage=leverage,
        client_order_id=client_order_id,
        notional_usd=notional_usd,
    )

    admission = admit(proposal, account_state, now=now)
    event = build_decision_event(
        trial_id=trial_id,
        actor=actor,
        proposal=proposal,
        admission=admission,
        trace_ref="runtime.runner.supervised_paper",
        ts=now,
    )
    event["inputs"]["account_state"] = dict(account_state)
    event["inputs"]["state_sources"] = account_payload["sources"]
    event["inputs"]["dry_run"] = dry_run
    event["venue"]["request"] = venue_request_summary(proposal)

    order_called = False
    if not admission.allowed:
        event["venue"]["response"] = {
            "not_called": True,
            "reason": "risk_gate_reject",
        }
    elif dry_run:
        event["venue"]["response"] = {
            "not_called": True,
            "reason": "dry_run",
        }
    else:
        order_called = True
        try:
            response = submit_paper_order(kraken_bin=kraken_path, proposal=proposal)
        except KrakenCommandError as exc:
            event["venue"]["response"] = {
                "ok": False,
                "error": str(exc),
                "returncode": exc.returncode,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            }
        else:
            event["venue"]["response"] = {
                "ok": True,
                "raw": response,
            }
            event["fills"] = extract_fills(response)

    path = append_decision_event(
        event,
        path=decision_jsonl_path(trial_id, aura_root=aura_root, repo_fallback=False),
        repo_fallback=False,
    )
    return SupervisedOrderResult(
        admission=admission,
        decision_path=path,
        event=event,
        account_state=account_state,
        order_called=order_called,
    )


def resolve_kraken_bin(kraken_bin: str | Path | None = None) -> str:
    """Resolve the Kraken binary, falling back to ~/.cargo/bin/kraken."""

    if kraken_bin is not None:
        return str(Path(kraken_bin).expanduser())

    discovered = shutil.which("kraken")
    if discovered is not None:
        return discovered
    return str(Path.home() / ".cargo" / "bin" / "kraken")


def read_paper_account_state(
    *,
    aura_root: str | Path | None,
    kraken_bin: str,
    observed_at: datetime,
) -> dict[str, Any]:
    """Read Kraken futures paper status/positions and map to risk inputs."""

    sources: dict[str, Any] = {
        "status_command": ["kraken", "futures", "paper", "status", "-o", "json"],
        "positions_command": ["kraken", "futures", "paper", "positions", "-o", "json"],
        "mapping_reasons": [],
    }
    status: Any = None
    positions: Any = None

    try:
        status = run_kraken_json(kraken_bin, ("futures", "paper", "status", "-o", "json"))
        sources["status_ok"] = True
    except KrakenCommandError as exc:
        sources["status_ok"] = False
        sources["mapping_reasons"].append(str(exc))

    try:
        positions = run_kraken_json(kraken_bin, ("futures", "paper", "positions", "-o", "json"))
        sources["positions_ok"] = True
    except KrakenCommandError as exc:
        sources["positions_ok"] = False
        sources["mapping_reasons"].append(str(exc))

    account_state = map_account_state(
        status=status,
        positions=positions,
        aura_root=aura_root,
        observed_at=observed_at,
        mapping_reasons=sources["mapping_reasons"],
    )
    return {
        "account_state": account_state,
        "status": status,
        "positions": positions,
        "sources": sources,
    }


def run_kraken_json(kraken_bin: str, args: Sequence[str]) -> Any:
    command = (kraken_bin, *args)
    completed = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise KrakenCommandError(command, completed.returncode, completed.stdout, completed.stderr)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise KrakenCommandError(command, None, completed.stdout, str(exc)) from exc


def map_account_state(
    *,
    status: Any,
    positions: Any,
    aura_root: str | Path | None,
    observed_at: datetime,
    mapping_reasons: list[str],
) -> dict[str, Any]:
    """Map live CLI JSON into the minimal ``admit`` account_state contract."""

    equity = first_numeric(
        status,
        (
            "equity",
            "account_equity",
            "accountEquity",
            "total_equity",
            "totalEquity",
            "margin_balance",
            "marginBalance",
            "collateral",
            "balance",
        ),
    )
    daily_pnl = first_numeric(
        status,
        (
            "daily_pnl",
            "dailyPnl",
            "day_pnl",
            "dayPnl",
            "pnl",
            "profit_loss",
            "profitLoss",
            "unrealized_pnl",
            "unrealizedPnl",
        ),
    )
    weekly_pnl = first_numeric(
        status,
        (
            "weekly_pnl",
            "weeklyPnl",
            "week_pnl",
            "weekPnl",
            "seven_day_pnl",
            "sevenDayPnl",
            "rolling_week_pnl",
            "rollingWeekPnl",
        ),
    )
    open_positions_count = open_position_count(positions)

    if equity is None:
        mapping_reasons.append("equity unavailable in futures paper status")
    if daily_pnl is None:
        mapping_reasons.append("daily_pnl unavailable in futures paper status")
    if weekly_pnl is None and daily_pnl is not None:
        # Kraken futures paper status exposes a single pnl field, not a weekly series.
        # Use that value as a paper-session weekly proxy and record the mapping.
        weekly_pnl = daily_pnl
        mapping_reasons.append(
            "weekly_pnl absent in futures paper status; using pnl/daily_pnl as paper-session proxy"
        )
    elif weekly_pnl is None:
        mapping_reasons.append("weekly_pnl unavailable in futures paper status; failing closed")
    if open_positions_count is None:
        mapping_reasons.append("open_positions_count unavailable in futures paper positions")

    return {
        "equity": equity,
        "open_positions_count": open_positions_count,
        "daily_pnl": daily_pnl,
        "weekly_pnl": weekly_pnl,
        "kill_state": read_kill_state(aura_root),
        "as_of": observed_at.isoformat().replace("+00:00", "Z"),
        "mapping_reasons": list(mapping_reasons),
    }


def read_kill_state(aura_root: str | Path | None) -> str:
    root = Path(aura_root) if aura_root is not None else Path("/var/aura")
    path = root / "paper" / "kill_state"
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except FileNotFoundError:
        return "armed"
    if value in {"soft", "hard"}:
        return value
    return value or "invalid"


def build_proposal(
    *,
    symbol: str,
    side: str,
    size: str,
    order_type: str,
    leverage: str,
    client_order_id: str,
    notional_usd: str | None,
) -> dict[str, Any]:
    proposal: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "size": size,
        "order_type": order_type,
        "leverage": leverage,
        "client_order_id": client_order_id,
    }
    if notional_usd not in (None, ""):
        proposal["notional_usd"] = notional_usd
    return proposal


def venue_request_summary(proposal: Mapping[str, Any]) -> dict[str, Any]:
    side = str(proposal["side"])
    return {
        "command": [
            "kraken",
            "futures",
            "paper",
            side,
            str(proposal["symbol"]),
            str(proposal["size"]),
            "--type",
            str(proposal["order_type"]),
            "--client-order-id",
            str(proposal["client_order_id"]),
            "-o",
            "json",
        ],
        "proposal": dict(proposal),
    }


def submit_paper_order(*, kraken_bin: str, proposal: Mapping[str, Any]) -> Any:
    side = str(proposal["side"])
    if side not in {"buy", "sell"}:
        raise KrakenCommandError(("kraken", "futures", "paper", side), None, "", "invalid side")
    return run_kraken_json(
        kraken_bin,
        (
            "futures",
            "paper",
            side,
            str(proposal["symbol"]),
            str(proposal["size"]),
            "--type",
            str(proposal["order_type"]),
            "--client-order-id",
            str(proposal["client_order_id"]),
            "-o",
            "json",
        ),
    )


def first_numeric(payload: Any, keys: Sequence[str]) -> str | None:
    normalized_keys = {normalize_key(key) for key in keys}
    for value in walk_key_values(payload):
        key, raw_value = value
        if normalize_key(key) in normalized_keys:
            numeric = decimal_string(raw_value)
            if numeric is not None:
                return numeric
    return None


def open_position_count(payload: Any) -> int | None:
    positions = extract_positions(payload)
    if positions is None:
        return None
    return sum(1 for position in positions if position_is_open(position))


def extract_positions(payload: Any) -> list[Any] | None:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, Mapping):
        return None
    for key in ("positions", "open_positions", "openPositions", "data", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    if all(isinstance(value, Mapping) for value in payload.values()):
        return list(payload.values())
    return None


def position_is_open(position: Any) -> bool:
    if not isinstance(position, Mapping):
        return bool(position)
    for key in (
        "size",
        "qty",
        "quantity",
        "contracts",
        "position",
        "position_size",
        "positionSize",
        "current_qty",
        "currentQty",
    ):
        if key in position:
            numeric = decimal_value(position[key])
            if numeric is not None:
                return numeric != 0
    return bool(position)


def extract_fills(response: Any) -> list[Any]:
    fills = find_first_list(response, ("fills", "executions", "trades"))
    return fills if fills is not None else []


def find_first_list(payload: Any, keys: Sequence[str]) -> list[Any] | None:
    normalized_keys = {normalize_key(key) for key in keys}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if normalize_key(key) in normalized_keys and isinstance(value, list):
                return value
        for value in payload.values():
            found = find_first_list(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_first_list(value, keys)
            if found is not None:
                return found
    return None


def walk_key_values(payload: Any) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            values.append((str(key), value))
            values.extend(walk_key_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(walk_key_values(value))
    return values


def normalize_key(value: str) -> str:
    return value.replace("-", "_").replace(" ", "_").lower()


def decimal_string(raw_value: Any) -> str | None:
    value = decimal_value(raw_value)
    if value is None:
        return None
    return format(value, "f")


def decimal_value(raw_value: Any) -> Decimal | None:
    if raw_value in (None, ""):
        return None
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite():
        return None
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(description="Run one human-triggered Kraken futures paper order.")
    parser.add_argument("--trial-id", required=True, help="trial id for evidence/trials/{trial_id}")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="futures paper symbol")
    parser.add_argument("--side", choices=("buy", "sell"), required=True, help="paper order side")
    parser.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help="paper order size; default 0.001 is intended to be tiny for PF_XBTUSD",
    )
    parser.add_argument("--leverage", default=DEFAULT_LEVERAGE, help="proposal leverage, capped at 2x")
    parser.add_argument("--client-order-id", required=True, help="human-supplied paper client order id")
    parser.add_argument("--order-type", default=DEFAULT_ORDER_TYPE, help="Kraken futures paper order type")
    parser.add_argument(
        "--notional-usd",
        help="proposal notional for risk admission; market orders reject without it",
    )
    parser.add_argument("--dry-run", action="store_true", help="admit and write JSONL, but skip order")
    parser.add_argument("--aura-root", help="override AURA_ROOT; production default is /var/aura")
    parser.add_argument("--actor", default=DEFAULT_ACTOR, help="actor label for decision JSONL")
    args = parser.parse_args(argv)

    result = run_supervised_order(
        trial_id=args.trial_id,
        symbol=args.symbol,
        side=args.side,
        size=args.size,
        leverage=args.leverage,
        client_order_id=args.client_order_id,
        order_type=args.order_type,
        notional_usd=args.notional_usd,
        aura_root=args.aura_root,
        dry_run=args.dry_run,
        actor=args.actor,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if result.admission.allowed and (
        result.event.get("venue", {}).get("response", {}).get("ok") is False
    ):
        return 1
    return 0 if result.admission.allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
