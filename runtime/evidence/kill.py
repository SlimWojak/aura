"""Kill-drill JSONL helpers for paper runtime operations."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Mapping

from runtime.evidence.decision import decision_jsonl_path


KILL_EVENT_SCHEMA = "aura.kill_event.v1"


def build_kill_event(
    *,
    trial_id: str,
    actor: str,
    action: str,
    kill_state: str,
    aura_root: str | Path | None,
    intent: str,
    details: Mapping[str, Any] | None = None,
    ok: bool = True,
    ts: datetime | None = None,
) -> dict[str, Any]:
    """Build a human-auditable paper kill-switch ops event."""

    event_time = _event_time(ts)
    return {
        "schema": KILL_EVENT_SCHEMA,
        "ts": event_time.isoformat().replace("+00:00", "Z"),
        "trial_id": trial_id,
        "actor": actor,
        "intent": intent,
        "action": action,
        "kill_state": kill_state,
        "ok": ok,
        "paper_only": True,
        "human_auditable": True,
        "aura_root": str(aura_root) if aura_root is not None else "${AURA_ROOT:-/var/aura}",
        "details": dict(details or {}),
    }


def append_kill_event(
    event: Mapping[str, Any],
    *,
    aura_root: str | Path | None = None,
    path: str | Path | None = None,
) -> Path:
    """Append one kill-drill ops event as JSONL."""

    output_path = Path(path) if path is not None else decision_jsonl_path(
        str(event["trial_id"]),
        aura_root=aura_root,
        repo_fallback=False,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True, separators=(",", ":")))
        handle.write("\n")
    return output_path


def _event_time(ts: datetime | None) -> datetime:
    if ts is None:
        return datetime.now(tz=UTC)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)
