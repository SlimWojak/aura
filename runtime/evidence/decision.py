"""Decision-event JSONL helpers for paper runtime evidence."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping

from runtime.risk import AdmissionResult


SCHEMA_ID = "aura.decision_event.v1"
DEFAULT_AURA_ROOT = Path("/var/aura")
REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "decision_event.schema.json"
VALID_INTENTS = {"open", "close", "cancel", "hold", "risk_reject"}
VALID_RISK_RESULTS = {"allow", "reject"}


class DecisionEventValidationError(ValueError):
    """Raised when a decision event does not match the lightweight schema."""


def decision_jsonl_path(
    trial_id: str,
    *,
    aura_root: str | Path | None = None,
    repo_fallback: bool = False,
) -> Path:
    """Return the decision JSONL path for a trial.

    Production defaults to AURA_ROOT or /var/aura. Tests and human-triggered
    smoke runs can set repo_fallback=True to write under repo-local evidence.
    """

    root = _evidence_root(aura_root=aura_root, repo_fallback=repo_fallback)
    return root / "trials" / trial_id / "decision.jsonl"


def build_decision_event(
    *,
    trial_id: str,
    actor: str,
    proposal: Mapping[str, Any],
    admission: AdmissionResult,
    intent: str | None = None,
    hypothesis_id: str | None = None,
    venue_name: str = "kraken-futures-paper",
    trace_ref: str = "",
    ts: datetime | None = None,
) -> dict[str, Any]:
    """Build an allow/reject decision event from an admission result."""

    event_time = _event_time(ts)
    event_intent = intent if intent is not None else ("open" if admission.allowed else "risk_reject")
    event: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "ts": event_time.isoformat().replace("+00:00", "Z"),
        "trial_id": trial_id,
        "actor": actor,
        "intent": event_intent,
        "inputs": {
            "proposal": dict(proposal),
        },
        "risk_gate": {
            "result": admission.result,
            "reasons": list(admission.reasons),
            "policy_version": admission.policy_version,
        },
        "venue": {
            "name": venue_name,
            "request": dict(proposal),
            "response": {},
            "client_order_id": proposal.get("client_order_id", ""),
        },
        "fills": [],
        "pnl_delta_paper": None,
        "trace_ref": trace_ref,
        "human_auditable": True,
    }
    if hypothesis_id is not None:
        event["hypothesis_id"] = hypothesis_id
    return event


def append_decision_event(
    event: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    repo_fallback: bool = True,
) -> Path:
    """Validate and append one decision event as JSONL."""

    validate_decision_event(event)
    output_path = Path(path) if path is not None else decision_jsonl_path(
        str(event["trial_id"]),
        repo_fallback=False,
    )
    try:
        _append_jsonl(output_path, event)
        return output_path
    except OSError:
        if path is not None or not repo_fallback:
            raise
        fallback_path = decision_jsonl_path(str(event["trial_id"]), repo_fallback=True)
        _append_jsonl(fallback_path, event)
        return fallback_path


def validate_decision_event(event: Mapping[str, Any]) -> None:
    """Lightweight validation for schemas/decision_event.schema.json."""

    required = ("schema", "ts", "trial_id", "actor", "intent", "risk_gate", "venue")
    for field_name in required:
        if field_name not in event:
            raise DecisionEventValidationError(f"missing required field: {field_name}")

    if event["schema"] != SCHEMA_ID:
        raise DecisionEventValidationError("schema must be aura.decision_event.v1")
    if not isinstance(event["ts"], str):
        raise DecisionEventValidationError("ts must be a string")
    if _parse_datetime(event["ts"]) is None:
        raise DecisionEventValidationError("ts must be an ISO date-time string")
    if event["intent"] not in VALID_INTENTS:
        raise DecisionEventValidationError("intent is not in schema enum")

    risk_gate = event["risk_gate"]
    if not isinstance(risk_gate, Mapping):
        raise DecisionEventValidationError("risk_gate must be an object")
    for field_name in ("result", "policy_version"):
        if field_name not in risk_gate:
            raise DecisionEventValidationError(f"risk_gate missing required field: {field_name}")
    if risk_gate["result"] not in VALID_RISK_RESULTS:
        raise DecisionEventValidationError("risk_gate.result is not in schema enum")
    if "reasons" in risk_gate and not isinstance(risk_gate["reasons"], list):
        raise DecisionEventValidationError("risk_gate.reasons must be an array")

    if not isinstance(event["venue"], Mapping):
        raise DecisionEventValidationError("venue must be an object")


def _evidence_root(*, aura_root: str | Path | None, repo_fallback: bool) -> Path:
    if repo_fallback:
        return REPO_ROOT / "evidence"
    if aura_root is not None:
        return Path(aura_root) / "evidence"
    return Path(os.environ.get("AURA_ROOT", str(DEFAULT_AURA_ROOT))) / "evidence"


def _append_jsonl(path: Path, event: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _event_time(ts: datetime | None) -> datetime:
    if ts is None:
        return datetime.now(tz=UTC)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _parse_datetime(value: str) -> datetime | None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)

