"""Dedicated hard-kill flatten path for Kraken futures paper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from runtime.evidence import append_kill_event, build_kill_event, decision_jsonl_path
from runtime.kill_state import kill_state_path, write_kill_state_file
from runtime.runner.supervised_paper import (
    KrakenCommandError,
    decimal_value,
    extract_fills,
    extract_positions,
    position_is_open,
    resolve_kraken_bin,
    run_kraken_json,
    submit_paper_order,
)


DEFAULT_ACTOR = "ops:kill_drill"
FLATTEN_ORDER_TYPE = "market"


@dataclass(frozen=True, slots=True)
class FlattenOrder:
    """One paper market order needed to flatten an open futures paper position."""

    symbol: str
    side: str
    size: str
    client_order_id: str
    source_position: Mapping[str, Any]

    def proposal(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "order_type": FLATTEN_ORDER_TYPE,
            "leverage": "1",
            "client_order_id": self.client_order_id,
        }


@dataclass(frozen=True, slots=True)
class KillActionResult:
    """Result for one hard-kill cancel, inspect, or flatten action."""

    action: str
    ok: bool
    command: tuple[str, ...]
    response: Any = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": self.action,
            "ok": self.ok,
            "command": list(self.command),
        }
        if self.response is not None:
            payload["response"] = self.response
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True, slots=True)
class HardKillResult:
    """Summary returned by the hard-kill paper flatten path."""

    trial_id: str
    decision_path: Path
    kill_state_path: Path
    cancel_all: KillActionResult
    positions_read: KillActionResult
    flatten_actions: tuple[KillActionResult, ...]

    @property
    def ok(self) -> bool:
        return (
            self.cancel_all.ok
            and self.positions_read.ok
            and all(action.ok for action in self.flatten_actions)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "decision_jsonl": str(self.decision_path),
            "kill_state_path": str(self.kill_state_path),
            "ok": self.ok,
            "cancel_all": self.cancel_all.to_dict(),
            "positions_read": self.positions_read.to_dict(),
            "flatten_actions": [action.to_dict() for action in self.flatten_actions],
        }


def run_hard_kill(
    *,
    trial_id: str,
    aura_root: str | Path | None = None,
    actor: str = DEFAULT_ACTOR,
    kraken_bin: str | Path | None = None,
    force: bool = True,
    ts: datetime | None = None,
) -> HardKillResult:
    """Set hard kill, cancel all, and flatten futures paper positions.

    This is the explicit escape hatch for kill handling. It never calls
    ``admit()`` because hard kill deliberately blocks normal admissions.
    """

    if not force:
        raise ValueError("hard kill flatten requires force=True")

    now = _event_time(ts)
    kraken_path = resolve_kraken_bin(kraken_bin)
    output_path = decision_jsonl_path(trial_id, aura_root=aura_root, repo_fallback=False)
    state_path = write_kill_state_file("hard", aura_root)
    append_kill_event(
        build_kill_event(
            trial_id=trial_id,
            actor=actor,
            action="set_hard",
            kill_state="hard",
            aura_root=aura_root,
            intent="kill_hard",
            details={
                "kill_state_path": str(state_path),
                "force": force,
                "kill_override": True,
            },
            ts=now,
        ),
        path=output_path,
    )

    cancel_all = _run_action(
        action="cancel_all",
        kraken_bin=kraken_path,
        args=("futures", "paper", "cancel-all", "-o", "json"),
    )
    _append_action_event(
        trial_id=trial_id,
        actor=actor,
        aura_root=aura_root,
        output_path=output_path,
        action_result=cancel_all,
        intent="kill_cancel_all",
        extra={"force": force, "kill_override": True},
        ts=now,
    )

    positions_read = _run_action(
        action="positions_read",
        kraken_bin=kraken_path,
        args=("futures", "paper", "positions", "-o", "json"),
    )
    _append_action_event(
        trial_id=trial_id,
        actor=actor,
        aura_root=aura_root,
        output_path=output_path,
        action_result=positions_read,
        intent="kill_positions_read",
        extra={"force": force, "kill_override": True},
        ts=now,
    )

    flatten_actions: list[KillActionResult] = []
    positions = extract_positions(positions_read.response) if positions_read.ok else None
    if positions is not None:
        open_positions = [position for position in positions if position_is_open(position)]
        for index, position in enumerate(open_positions, start=1):
            flatten_order = flatten_order_from_position(
                position,
                trial_id=trial_id,
                index=index,
            )
            if flatten_order is None:
                action_result = KillActionResult(
                    action="flatten_skip",
                    ok=False,
                    command=(),
                    response={"position": position},
                    error="could not infer symbol, side, or size for open position",
                )
            else:
                action_result = _submit_flatten_order(
                    kraken_bin=kraken_path,
                    flatten_order=flatten_order,
                )
            flatten_actions.append(action_result)
            _append_action_event(
                trial_id=trial_id,
                actor=actor,
                aura_root=aura_root,
                output_path=output_path,
                action_result=action_result,
                intent="kill_flatten",
                extra={
                    "force": force,
                    "kill_override": True,
                    "source_position": position,
                },
                ts=now,
            )

    return HardKillResult(
        trial_id=trial_id,
        decision_path=output_path,
        kill_state_path=kill_state_path(aura_root),
        cancel_all=cancel_all,
        positions_read=positions_read,
        flatten_actions=tuple(flatten_actions),
    )


def flatten_order_from_position(
    position: Any,
    *,
    trial_id: str,
    index: int,
) -> FlattenOrder | None:
    if not isinstance(position, Mapping):
        return None

    symbol = _first_text(
        position,
        (
            "symbol",
            "instrument",
            "instrument_name",
            "instrumentName",
            "pair",
            "ticker",
            "contract",
        ),
    )
    signed_size = _position_size(position)
    if symbol is None or signed_size is None or signed_size == 0:
        return None

    side = _flatten_side(position, signed_size)
    if side is None:
        return None

    return FlattenOrder(
        symbol=symbol,
        side=side,
        size=format(abs(signed_size), "f"),
        client_order_id=_flatten_client_order_id(trial_id, index),
        source_position=position,
    )


def paper_command_display(args: Sequence[str]) -> tuple[str, ...]:
    _ensure_futures_paper_args(args)
    return ("kraken", *args)


def _run_action(*, action: str, kraken_bin: str, args: Sequence[str]) -> KillActionResult:
    _ensure_futures_paper_args(args)
    command = paper_command_display(args)
    try:
        response = run_kraken_json(kraken_bin, args)
    except KrakenCommandError as exc:
        return KillActionResult(
            action=action,
            ok=False,
            command=command,
            error=str(exc),
            response={
                "returncode": exc.returncode,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            },
        )
    return KillActionResult(action=action, ok=True, command=command, response=response)


def _submit_flatten_order(*, kraken_bin: str, flatten_order: FlattenOrder) -> KillActionResult:
    proposal = flatten_order.proposal()
    args = (
        "futures",
        "paper",
        proposal["side"],
        proposal["symbol"],
        proposal["size"],
        "--type",
        proposal["order_type"],
        "--client-order-id",
        proposal["client_order_id"],
        "-o",
        "json",
    )
    command = paper_command_display(args)
    try:
        response = submit_paper_order(kraken_bin=kraken_bin, proposal=proposal)
    except KrakenCommandError as exc:
        return KillActionResult(
            action="flatten_order",
            ok=False,
            command=command,
            error=str(exc),
            response={
                "returncode": exc.returncode,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            },
        )
    return KillActionResult(
        action="flatten_order",
        ok=True,
        command=command,
        response={
            "raw": response,
            "fills": extract_fills(response),
            "proposal": proposal,
        },
    )


def _append_action_event(
    *,
    trial_id: str,
    actor: str,
    aura_root: str | Path | None,
    output_path: Path,
    action_result: KillActionResult,
    intent: str,
    extra: Mapping[str, Any],
    ts: datetime,
) -> None:
    append_kill_event(
        build_kill_event(
            trial_id=trial_id,
            actor=actor,
            action=action_result.action,
            kill_state="hard",
            aura_root=aura_root,
            intent=intent,
            ok=action_result.ok,
            details={
                **dict(extra),
                **action_result.to_dict(),
            },
            ts=ts,
        ),
        path=output_path,
    )


def _ensure_futures_paper_args(args: Sequence[str]) -> None:
    if tuple(args[:2]) != ("futures", "paper"):
        raise ValueError("kill path only permits kraken futures paper commands")
    forbidden = {"--allow-dangerous", "funding", "earn", "withdraw", "live", "all"}
    if any(part in forbidden for part in args):
        raise ValueError("forbidden Kraken scope or flag in kill path")


def _position_size(position: Mapping[str, Any]) -> Decimal | None:
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
        "open_size",
        "openSize",
        "balance",
        "amount",
    ):
        if key in position:
            value = decimal_value(position[key])
            if value is not None:
                return value
    return None


def _flatten_side(position: Mapping[str, Any], signed_size: Decimal) -> str | None:
    side_text = _first_text(
        position,
        (
            "side",
            "direction",
            "position_side",
            "positionSide",
            "long_short",
            "longShort",
        ),
    )
    if side_text is not None:
        normalized = side_text.replace("_", "").replace("-", "").replace(" ", "").lower()
        if normalized in {"long", "buy", "bought", "bid"}:
            return "sell"
        if normalized in {"short", "sell", "sold", "ask"}:
            return "buy"

    if signed_size > 0:
        return "sell"
    if signed_size < 0:
        return "buy"
    return None


def _first_text(position: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = position.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _flatten_client_order_id(trial_id: str, index: int) -> str:
    safe_trial = "".join(
        character.lower() if character.isalnum() else "-"
        for character in trial_id
    ).strip("-")
    safe_trial = safe_trial[:32] or "kill"
    return f"aura-kill-{safe_trial}-{index}"


def _event_time(ts: datetime | None) -> datetime:
    if ts is None:
        return datetime.now(tz=UTC)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)
