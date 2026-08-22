"""Human-triggered smoke check for the paper risk admission stub."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from runtime.evidence import append_decision_event, build_decision_event, decision_jsonl_path
from runtime.risk import admit


TRIAL_ID = "T-admit-smoke"


def main() -> int:
    parser = ArgumentParser(description="Run a paper-only risk admission smoke check.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="append dry-run decision JSONL under repo evidence/trials/T-admit-smoke/",
    )
    args = parser.parse_args()

    now = datetime.now(tz=UTC)
    account_state = {
        "equity": 10_000,
        "open_positions_count": 0,
        "daily_pnl": 0,
        "weekly_pnl": 0,
        "kill_state": "armed",
        "as_of": now.isoformat().replace("+00:00", "Z"),
    }
    proposals = [
        {
            "symbol": "PF_XBTUSD",
            "side": "buy",
            "size": 0.01,
            "order_type": "limit",
            "price_usd": 45_000,
            "leverage": 1,
            "client_order_id": "smoke-under-limit",
        },
        {
            "symbol": "PF_XBTUSD",
            "side": "buy",
            "size": 0.02,
            "order_type": "limit",
            "notional_usd": 900,
            "leverage": 1,
            "client_order_id": "smoke-over-limit",
        },
    ]

    rows: list[dict[str, Any]] = []
    written_path: Path | None = None
    for proposal in proposals:
        admission = admit(proposal, account_state, now=now)
        row = {
            "proposal": proposal,
            "admission": admission.to_dict(),
        }
        rows.append(row)
        if args.write:
            event = build_decision_event(
                trial_id=TRIAL_ID,
                actor="cos:admit_smoke",
                proposal=proposal,
                admission=admission,
                trace_ref="runtime.tools.admit_smoke",
                ts=now,
            )
            written_path = append_decision_event(
                event,
                path=decision_jsonl_path(TRIAL_ID, repo_fallback=True),
            )

    output: dict[str, Any] = {"results": rows}
    if written_path is not None:
        output["decision_jsonl"] = str(written_path)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

