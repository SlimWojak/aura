"""Thin ledger scorer for Aura paper trial evidence."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


TRIAL_LEDGER_SCHEMA = "aura.trial_ledger_summary.v1"
DEFAULT_AURA_ROOT = Path("/var/aura")


def score_trials(*, aura_root: str | Path | None = None) -> dict[str, Any]:
    """Summarize ``$AURA_ROOT/evidence/trials/*/decision.jsonl``."""

    root = _aura_root(aura_root)
    evidence_root = root / "evidence"
    trials_root = evidence_root / "trials"
    ledger_root = evidence_root / "ledger"
    decision_files = sorted(trials_root.glob("*/decision.jsonl")) if trials_root.exists() else []
    by_schema: Counter[str] = Counter()
    by_intent: Counter[str] = Counter()
    by_bias: Counter[str] = Counter()
    by_risk_result: Counter[str] = Counter()
    by_trial: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    event_count = 0
    events_with_fills = 0
    fill_price_count = 0
    explicit_pnl_sum = Decimal("0")
    explicit_pnl_count = 0

    for decision_file in decision_files:
        trial_id = decision_file.parent.name
        trial_summary = {
            "event_count": 0,
            "schemas": Counter(),
            "intents": Counter(),
            "biases": Counter(),
            "risk_results": Counter(),
        }
        for line_number, event in _read_jsonl(decision_file, errors):
            event_count += 1
            trial_summary["event_count"] += 1
            schema = _string_or_unknown(event.get("schema"))
            intent = _string_or_unknown(event.get("intent"))
            bias = _extract_bias(event)
            risk_result = _extract_risk_result(event)
            by_schema[schema] += 1
            by_intent[intent] += 1
            trial_summary["schemas"][schema] += 1
            trial_summary["intents"][intent] += 1
            if bias is not None:
                by_bias[bias] += 1
                trial_summary["biases"][bias] += 1
            if risk_result is not None:
                by_risk_result[risk_result] += 1
                trial_summary["risk_results"][risk_result] += 1

            fills = event.get("fills")
            if isinstance(fills, list) and fills:
                events_with_fills += 1
                fill_price_count += _count_fill_prices(fills)
            explicit_pnl = _decimal_or_none(event.get("pnl_delta_paper"))
            if explicit_pnl is not None:
                explicit_pnl_count += 1
                explicit_pnl_sum += explicit_pnl

        by_trial[trial_id] = _freeze_trial_summary(trial_summary, line_count=trial_summary["event_count"])

    summary: dict[str, Any] = {
        "schema": TRIAL_LEDGER_SCHEMA,
        "ok": not errors,
        "generated_at": utc_now_iso(),
        "aura_root": str(root),
        "evidence_root": str(evidence_root),
        "trials_scanned": len(decision_files),
        "decision_files": [str(path) for path in decision_files],
        "event_count": event_count,
        "counts": {
            "by_schema": dict(sorted(by_schema.items())),
            "by_intent": dict(sorted(by_intent.items())),
            "by_bias": dict(sorted(by_bias.items())),
            "by_risk_result": dict(sorted(by_risk_result.items())),
        },
        "paper": {
            "events_with_fills": events_with_fills,
            "fill_price_count": fill_price_count,
            "pnl_note": (
                "No PnL is invented from paper fills. realized_pnl_paper is "
                "reported only when events carry explicit numeric pnl_delta_paper."
            ),
        },
        "trials": by_trial,
        "errors": errors,
    }
    if explicit_pnl_count:
        summary["paper"]["realized_pnl_paper"] = format(explicit_pnl_sum, "f")
        summary["paper"]["pnl_event_count"] = explicit_pnl_count
    return summary


def write_summary(summary: Mapping[str, Any], *, aura_root: str | Path | None = None) -> Path:
    """Write the ledger summary JSON under ``$AURA_ROOT/evidence/ledger``."""

    root = _aura_root(aura_root)
    output_path = root / "evidence" / "ledger" / "summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _aura_root(aura_root: str | Path | None) -> Path:
    if aura_root is not None:
        return Path(aura_root)
    return Path(os.environ.get("AURA_ROOT", str(DEFAULT_AURA_ROOT)))


def _read_jsonl(path: Path, errors: list[dict[str, Any]]) -> Iterable[tuple[int, Mapping[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(
                    {
                        "path": str(path),
                        "line": line_number,
                        "error": str(exc),
                    }
                )
                continue
            if not isinstance(payload, Mapping):
                errors.append(
                    {
                        "path": str(path),
                        "line": line_number,
                        "error": "event must be a JSON object",
                    }
                )
                continue
            yield line_number, payload


def _extract_bias(event: Mapping[str, Any]) -> str | None:
    signal = event.get("signal")
    if isinstance(signal, Mapping):
        bias = signal.get("bias")
        if isinstance(bias, str):
            return bias
    bias = event.get("bias")
    return bias if isinstance(bias, str) else None


def _extract_risk_result(event: Mapping[str, Any]) -> str | None:
    risk_gate = event.get("risk_gate")
    if not isinstance(risk_gate, Mapping):
        return None
    result = risk_gate.get("result")
    return result if isinstance(result, str) else None


def _count_fill_prices(fills: Iterable[Any]) -> int:
    count = 0
    for fill in fills:
        if isinstance(fill, Mapping):
            price = fill.get("price")
            if price is None:
                price = fill.get("fill_price")
            if price is None:
                price = fill.get("fillPrice")
            if _decimal_or_none(price) is not None:
                count += 1
    return count


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return decimal if decimal.is_finite() else None


def _string_or_unknown(value: Any) -> str:
    return value if isinstance(value, str) and value else "unknown"


def _freeze_trial_summary(summary: Mapping[str, Any], *, line_count: int) -> dict[str, Any]:
    return {
        "event_count": line_count,
        "schemas": dict(sorted(summary["schemas"].items())),
        "intents": dict(sorted(summary["intents"].items())),
        "biases": dict(sorted(summary["biases"].items())),
        "risk_results": dict(sorted(summary["risk_results"].items())),
    }
