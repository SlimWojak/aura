from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import TestCase
from unittest.mock import patch

from runtime.runner import run_supervised_order
from runtime.runner.supervised_paper import map_account_state


def completed(payload):
    return subprocess.CompletedProcess(
        args=["kraken"],
        returncode=0,
        stdout=json.dumps(payload),
        stderr="",
    )


class SupervisedPaperRunnerTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_reject_writes_jsonl_and_does_not_call_order(self):
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            run.side_effect = [
                completed({"equity": 10_000, "pnl": 0, "weekly_pnl": 0}),
                completed([]),
            ]

            result = run_supervised_order(
                trial_id="T-reject",
                symbol="PF_XBTUSD",
                side="buy",
                size="0.001",
                leverage="1",
                client_order_id="aura-test-reject",
                notional_usd="501",
                aura_root=self.aura_root,
                kraken_bin="/tmp/kraken",
            )

        self.assertFalse(result.admission.allowed)
        self.assertFalse(result.order_called)
        self.assertEqual(2, run.call_count)
        self.assertEqual("risk_gate_reject", result.event["venue"]["response"]["reason"])
        self.assertEqual("reject", self.read_event("T-reject")["risk_gate"]["result"])

    def test_allow_calls_buy_once_and_writes_response(self):
        order_response = {
            "status": "ok",
            "order_id": "paper-1",
            "fills": [{"price": "100000", "size": "0.001"}],
        }
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            run.side_effect = [
                completed({"equity": 10_000, "pnl": 0, "weekly_pnl": 0}),
                completed([]),
                completed(order_response),
            ]

            result = run_supervised_order(
                trial_id="T-allow",
                symbol="PF_XBTUSD",
                side="buy",
                size="0.001",
                leverage="1",
                client_order_id="aura-test-allow",
                notional_usd="100",
                aura_root=self.aura_root,
                kraken_bin="/tmp/kraken",
            )

        self.assertTrue(result.admission.allowed)
        self.assertTrue(result.order_called)
        self.assertEqual(3, run.call_count)
        self.assertEqual("buy", run.call_args_list[2].args[0][3])
        event = self.read_event("T-allow")
        self.assertEqual("allow", event["risk_gate"]["result"])
        self.assertEqual(order_response, event["venue"]["response"]["raw"])
        self.assertEqual(order_response["fills"], event["fills"])

    def test_dry_run_never_calls_order_when_allowed(self):
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            run.side_effect = [
                completed({"equity": 10_000, "pnl": 0, "weekly_pnl": 0}),
                completed([]),
            ]

            result = run_supervised_order(
                trial_id="T-dry-run",
                symbol="PF_XBTUSD",
                side="sell",
                size="0.001",
                leverage="1",
                client_order_id="aura-test-dry-run",
                notional_usd="100",
                aura_root=self.aura_root,
                dry_run=True,
                kraken_bin="/tmp/kraken",
            )

        self.assertTrue(result.admission.allowed)
        self.assertFalse(result.order_called)
        self.assertEqual(2, run.call_count)
        event = self.read_event("T-dry-run")
        self.assertEqual("allow", event["risk_gate"]["result"])
        self.assertEqual("dry_run", event["venue"]["response"]["reason"])

    def test_missing_weekly_uses_pnl_as_session_proxy(self):
        status = {"equity": "10000", "pnl": "-1.5", "positions": 0}
        positions = {"positions": []}
        state = map_account_state(
            status=status,
            positions=positions,
            aura_root=None,
            observed_at=__import__('datetime').datetime.now(__import__('datetime').UTC),
            mapping_reasons=[],
        )
        self.assertEqual(state["daily_pnl"], "-1.5")
        self.assertEqual(state["weekly_pnl"], "-1.5")
        self.assertTrue(
            any("paper-session proxy" in reason for reason in state["mapping_reasons"])
        )

    def read_event(self, trial_id):
        path = self.aura_root / "evidence" / "trials" / trial_id / "decision.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, len(lines))
        return json.loads(lines[0])


if __name__ == "__main__":
    unittest.main()
