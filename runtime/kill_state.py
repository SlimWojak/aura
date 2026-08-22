"""Paper kill-state and heartbeat file helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path


DEFAULT_AURA_ROOT = Path("/var/aura")
VALID_KILL_STATES = {"armed", "soft", "hard"}


def aura_root_path(aura_root: str | Path | None = None) -> Path:
    if aura_root is not None:
        return Path(aura_root)
    return Path(os.environ.get("AURA_ROOT", str(DEFAULT_AURA_ROOT)))


def paper_dir(aura_root: str | Path | None = None) -> Path:
    return aura_root_path(aura_root) / "paper"


def kill_state_path(aura_root: str | Path | None = None) -> Path:
    return paper_dir(aura_root) / "kill_state"


def heartbeat_path(aura_root: str | Path | None = None) -> Path:
    return paper_dir(aura_root) / "heartbeat"


def read_kill_state_file(aura_root: str | Path | None = None) -> str:
    path = kill_state_path(aura_root)
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except FileNotFoundError:
        return "armed"
    if value in VALID_KILL_STATES:
        return value
    return value or "invalid"


def write_kill_state_file(state: str, aura_root: str | Path | None = None) -> Path:
    normalized = state.strip().lower()
    if normalized not in VALID_KILL_STATES:
        raise ValueError(f"invalid kill_state: {state}")
    path = kill_state_path(aura_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{normalized}\n", encoding="utf-8")
    return path


def delete_kill_state_file(aura_root: str | Path | None = None) -> bool:
    path = kill_state_path(aura_root)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def write_heartbeat(aura_root: str | Path | None = None, ts: datetime | None = None) -> Path:
    event_time = _event_time(ts)
    path = heartbeat_path(aura_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(event_time.isoformat().replace("+00:00", "Z") + "\n", encoding="utf-8")
    return path


def read_heartbeat(aura_root: str | Path | None = None) -> datetime | None:
    path = heartbeat_path(aura_root)
    try:
        raw_value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not raw_value:
        return None
    normalized = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return _event_time(parsed)


def heartbeat_age_seconds(
    aura_root: str | Path | None = None,
    *,
    now: datetime | None = None,
) -> float | None:
    heartbeat = read_heartbeat(aura_root)
    if heartbeat is None:
        return None
    return max(0.0, (_event_time(now) - heartbeat).total_seconds())


def _event_time(ts: datetime | None) -> datetime:
    if ts is None:
        return datetime.now(tz=UTC)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)
