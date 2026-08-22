"""Human-triggered kill-switch and dead-man drill CLI."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from runtime.evidence import append_kill_event, build_kill_event, decision_jsonl_path
from runtime.kill_state import (
    delete_kill_state_file,
    heartbeat_age_seconds,
    heartbeat_path,
    kill_state_path,
    read_heartbeat,
    read_kill_state_file,
    write_heartbeat,
    write_kill_state_file,
)
from runtime.risk import DEFAULT_POLICY
from runtime.runner.hard_flatten import run_hard_kill
from runtime.runner.supervised_paper import (
    DEFAULT_LEVERAGE,
    DEFAULT_SIZE,
    DEFAULT_SYMBOL,
    KrakenCommandError,
    decimal_value,
    extract_positions,
    position_is_open,
    resolve_kraken_bin,
    run_kraken_json,
    run_supervised_order,
)


DEFAULT_ACTOR = "ops:kill_drill"
DEFAULT_NOTIONAL_USD = "100"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 2
    if args.command in {"hard", "drill-b"} and not args.i_understand_paper:
        parser.error(f"{args.command} requires --i-understand-paper")

    try:
        result = dispatch(args)
    except (KrakenCommandError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 1


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Human-triggered Aura paper kill-switch drills.")
    command_parent = ArgumentParser(add_help=False)
    command_parent.add_argument("--aura-root", help="override AURA_ROOT; dexter default is /var/aura")
    command_parent.add_argument("--kraken-bin", help="path to kraken CLI")
    command_parent.add_argument("--actor", default=DEFAULT_ACTOR, help="actor label for JSONL evidence")
    command_parent.add_argument("--trial-id", help="evidence trial id; default is T-kill-...")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", parents=[command_parent], help="show kill, heartbeat, and paper positions")
    subparsers.add_parser("soft", parents=[command_parent], help="set soft kill and append JSONL")

    hard_parser = subparsers.add_parser(
        "hard",
        parents=[command_parent],
        help="set hard kill, cancel all paper orders, and flatten paper positions",
    )
    hard_parser.add_argument("--i-understand-paper", action="store_true", help="confirm futures paper kill action")

    arm_parser = subparsers.add_parser("arm", parents=[command_parent], help="clear kill state")
    arm_parser.add_argument("--delete", action="store_true", help="delete kill_state instead of writing armed")

    subparsers.add_parser("heartbeat", parents=[command_parent], help="write heartbeat timestamp now")

    deadman_parser = subparsers.add_parser(
        "deadman-check",
        parents=[command_parent],
        help="run hard kill if heartbeat is stale or missing",
    )
    deadman_parser.add_argument(
        "--dead-man-seconds",
        type=int,
        default=DEFAULT_POLICY.dead_man_seconds,
        help="heartbeat age threshold; default from RISK_POLICY is 600",
    )

    drill_a_parser = subparsers.add_parser(
        "drill-a",
        parents=[command_parent],
        help="soft kill drill: set soft and verify supervised entry rejects",
    )
    add_tiny_order_args(drill_a_parser)
    drill_a_parser.add_argument("--rearm", action="store_true", help="write armed after the drill")

    drill_b_parser = subparsers.add_parser(
        "drill-b",
        parents=[command_parent],
        help="hard kill drill: optionally open tiny paper position, then hard kill and verify flat",
    )
    add_tiny_order_args(drill_b_parser)
    drill_b_parser.add_argument("--skip-open", action="store_true", help="do not open a tiny position if flat")
    drill_b_parser.add_argument("--rearm", action="store_true", help="write armed after the drill")
    drill_b_parser.add_argument("--i-understand-paper", action="store_true", help="confirm futures paper drill")

    return parser


def add_tiny_order_args(parser: ArgumentParser) -> None:
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="futures paper symbol")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="tiny paper size; default 0.001")
    parser.add_argument("--notional-usd", default=DEFAULT_NOTIONAL_USD, help="risk notional for supervised open")


def dispatch(args: Namespace) -> dict[str, Any]:
    match args.command:
        case "status":
            return command_status(args)
        case "soft":
            return command_soft(args)
        case "hard":
            return command_hard(args)
        case "arm":
            return command_arm(args)
        case "heartbeat":
            return command_heartbeat(args)
        case "deadman-check":
            return command_deadman_check(args)
        case "drill-a":
            return command_drill_a(args)
        case "drill-b":
            return command_drill_b(args)
        case _:
            raise ValueError(f"unknown command: {args.command}")


def command_status(args: Namespace) -> dict[str, Any]:
    kraken_path = resolve_kraken_bin(args.kraken_bin)
    status_result = _read_kraken("status", kraken_path, ("futures", "paper", "status", "-o", "json"))
    positions_result = _read_kraken(
        "positions",
        kraken_path,
        ("futures", "paper", "positions", "-o", "json"),
    )
    heartbeat = read_heartbeat(args.aura_root)
    age = heartbeat_age_seconds(args.aura_root)
    return {
        "ok": status_result["ok"] and positions_result["ok"],
        "kill_state": read_kill_state_file(args.aura_root),
        "kill_state_path": str(kill_state_path(args.aura_root)),
        "heartbeat": {
            "path": str(heartbeat_path(args.aura_root)),
            "ts": _format_ts(heartbeat),
            "age_seconds": age,
        },
        "status": status_result,
        "positions": {
            **positions_result,
            "summary": positions_summary(positions_result.get("response")),
        },
    }


def command_soft(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "soft")
    state_path = write_kill_state_file("soft", args.aura_root)
    event_path = _append_simple_kill_event(
        trial_id=trial_id,
        actor=args.actor,
        aura_root=args.aura_root,
        action="set_soft",
        kill_state="soft",
        intent="kill_soft",
        details={"kill_state_path": str(state_path), "flatten_existing_positions": False},
    )
    return {
        "ok": True,
        "trial_id": trial_id,
        "kill_state": "soft",
        "kill_state_path": str(state_path),
        "decision_jsonl": str(event_path),
    }


def command_hard(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "hard")
    result = run_hard_kill(
        trial_id=trial_id,
        aura_root=args.aura_root,
        actor=args.actor,
        kraken_bin=args.kraken_bin,
        force=True,
    )
    return result.to_dict()


def command_arm(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "arm")
    if getattr(args, "delete", False):
        deleted = delete_kill_state_file(args.aura_root)
        details = {"deleted": deleted, "kill_state_path": str(kill_state_path(args.aura_root))}
    else:
        state_path = write_kill_state_file("armed", args.aura_root)
        details = {"deleted": False, "kill_state_path": str(state_path)}
    event_path = _append_simple_kill_event(
        trial_id=trial_id,
        actor=args.actor,
        aura_root=args.aura_root,
        action="arm",
        kill_state="armed",
        intent="kill_arm",
        details=details,
    )
    return {
        "ok": True,
        "trial_id": trial_id,
        "kill_state": read_kill_state_file(args.aura_root),
        "kill_state_path": str(kill_state_path(args.aura_root)),
        "decision_jsonl": str(event_path),
    }


def command_heartbeat(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "heartbeat")
    path = write_heartbeat(args.aura_root)
    event_path = _append_simple_kill_event(
        trial_id=trial_id,
        actor=args.actor,
        aura_root=args.aura_root,
        action="heartbeat",
        kill_state=read_kill_state_file(args.aura_root),
        intent="deadman_heartbeat",
        details={"heartbeat_path": str(path), "heartbeat_ts": path.read_text(encoding="utf-8").strip()},
    )
    return {
        "ok": True,
        "trial_id": trial_id,
        "heartbeat_path": str(path),
        "decision_jsonl": str(event_path),
    }


def command_deadman_check(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "deadman")
    heartbeat = read_heartbeat(args.aura_root)
    age = heartbeat_age_seconds(args.aura_root)
    stale = heartbeat is None or age is None or age > args.dead_man_seconds
    event_path = _append_simple_kill_event(
        trial_id=trial_id,
        actor=args.actor,
        aura_root=args.aura_root,
        action="deadman_check",
        kill_state=read_kill_state_file(args.aura_root),
        intent="deadman_check",
        details={
            "heartbeat_path": str(heartbeat_path(args.aura_root)),
            "heartbeat_ts": _format_ts(heartbeat),
            "heartbeat_age_seconds": age,
            "dead_man_seconds": args.dead_man_seconds,
            "stale": stale,
        },
    )
    if not stale:
        return {
            "ok": True,
            "trial_id": trial_id,
            "triggered": False,
            "decision_jsonl": str(event_path),
            "heartbeat_age_seconds": age,
            "dead_man_seconds": args.dead_man_seconds,
        }

    hard_result = run_hard_kill(
        trial_id=trial_id,
        aura_root=args.aura_root,
        actor=args.actor,
        kraken_bin=args.kraken_bin,
        force=True,
    )
    hard_payload = hard_result.to_dict()
    hard_payload["triggered"] = True
    hard_payload["heartbeat_age_seconds"] = age
    hard_payload["dead_man_seconds"] = args.dead_man_seconds
    return hard_payload


def command_drill_a(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "drill-a")
    soft_payload = command_soft(_with_trial_id(args, trial_id))
    supervised = run_supervised_order(
        trial_id=trial_id,
        symbol=args.symbol,
        side="buy",
        size=args.size,
        leverage=DEFAULT_LEVERAGE,
        client_order_id=f"aura-drill-a-{_safe_id(trial_id)}",
        notional_usd=args.notional_usd,
        aura_root=args.aura_root,
        actor=args.actor,
        kraken_bin=args.kraken_bin,
    )
    reasons = list(supervised.admission.reasons)
    passed = not supervised.order_called and "kill_state soft" in reasons
    payload: dict[str, Any] = {
        "ok": passed,
        "trial_id": trial_id,
        "soft": soft_payload,
        "supervised_attempt": supervised.to_dict(),
        "passed": passed,
        "left_soft": not args.rearm,
    }
    if args.rearm:
        payload["arm"] = command_arm(_with_trial_id(args, trial_id))
        payload["left_soft"] = False
    return payload


def command_drill_b(args: Namespace) -> dict[str, Any]:
    trial_id = _trial_id(args.trial_id, "drill-b")
    kraken_path = resolve_kraken_bin(args.kraken_bin)
    before_positions = _read_kraken(
        "positions",
        kraken_path,
        ("futures", "paper", "positions", "-o", "json"),
    )
    before_summary = positions_summary(before_positions.get("response"))
    opened_payload: dict[str, Any] | None = None

    if before_positions["ok"] and before_summary["open_count"] == 0 and not args.skip_open:
        opened = run_supervised_order(
            trial_id=trial_id,
            symbol=args.symbol,
            side="buy",
            size=args.size,
            leverage=DEFAULT_LEVERAGE,
            client_order_id=f"aura-drill-b-open-{_safe_id(trial_id)}",
            notional_usd=args.notional_usd,
            aura_root=args.aura_root,
            actor=args.actor,
            kraken_bin=args.kraken_bin,
        )
        opened_payload = opened.to_dict()
        open_response = opened.event.get("venue", {}).get("response", {})
        if not opened.admission.allowed or not opened.order_called or open_response.get("ok") is False:
            return {
                "ok": False,
                "trial_id": trial_id,
                "before_positions": before_summary,
                "opened": opened_payload,
                "error": "tiny supervised open did not succeed",
            }

    hard_result = run_hard_kill(
        trial_id=trial_id,
        aura_root=args.aura_root,
        actor=args.actor,
        kraken_bin=args.kraken_bin,
        force=True,
    )
    after_positions = _read_kraken(
        "positions",
        kraken_path,
        ("futures", "paper", "positions", "-o", "json"),
    )
    after_summary = positions_summary(after_positions.get("response"))
    passed = hard_result.ok and after_positions["ok"] and after_summary["open_count"] == 0
    payload: dict[str, Any] = {
        "ok": passed,
        "trial_id": trial_id,
        "before_positions": before_summary,
        "opened": opened_payload,
        "hard": hard_result.to_dict(),
        "after_positions": after_summary,
        "passed": passed,
    }
    if args.rearm:
        payload["arm"] = command_arm(_with_trial_id(args, trial_id))
    return payload


def positions_summary(payload: Any) -> dict[str, Any]:
    positions = extract_positions(payload)
    if positions is None:
        return {"open_count": None, "positions": []}
    open_positions = [position for position in positions if position_is_open(position)]
    return {
        "open_count": len(open_positions),
        "positions": [_position_summary(position) for position in open_positions],
    }


def _position_summary(position: Any) -> dict[str, Any]:
    if not isinstance(position, Mapping):
        return {"raw": position}
    return {
        "symbol": _first_text(position, ("symbol", "instrument", "instrumentName", "pair", "contract")),
        "side": _first_text(position, ("side", "direction", "positionSide", "longShort")),
        "size": _first_size(position),
        "raw": dict(position),
    }


def _read_kraken(label: str, kraken_bin: str, args: Sequence[str]) -> dict[str, Any]:
    command = ("kraken", *args)
    try:
        response = run_kraken_json(kraken_bin, args)
    except KrakenCommandError as exc:
        return {
            "label": label,
            "ok": False,
            "command": list(command),
            "error": str(exc),
            "response": {
                "returncode": exc.returncode,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            },
        }
    return {"label": label, "ok": True, "command": list(command), "response": response}


def _append_simple_kill_event(
    *,
    trial_id: str,
    actor: str,
    aura_root: str | Path | None,
    action: str,
    kill_state: str,
    intent: str,
    details: Mapping[str, Any],
) -> Path:
    event = build_kill_event(
        trial_id=trial_id,
        actor=actor,
        action=action,
        kill_state=kill_state,
        aura_root=aura_root,
        intent=intent,
        details=details,
    )
    return append_kill_event(
        event,
        path=decision_jsonl_path(trial_id, aura_root=aura_root, repo_fallback=False),
    )


def _trial_id(value: str | None, slug: str) -> str:
    if value:
        return value
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"T-kill-{slug}-{stamp}"


def _safe_id(value: str) -> str:
    safe = "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")
    return safe[:32] or "kill"


def _with_trial_id(args: Namespace, trial_id: str) -> Namespace:
    values = vars(args).copy()
    values["trial_id"] = trial_id
    return Namespace(**values)


def _format_ts(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _first_text(position: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = position.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _first_size(position: Mapping[str, Any]) -> str | None:
    for key in (
        "size",
        "qty",
        "quantity",
        "contracts",
        "position",
        "positionSize",
        "currentQty",
        "openSize",
        "amount",
    ):
        if key in position:
            value = decimal_value(position[key])
            if value is not None:
                return format(value.copy_abs(), "f")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
