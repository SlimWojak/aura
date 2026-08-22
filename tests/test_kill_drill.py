from __future__ import annotations

from argparse import Namespace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from runtime.kill_state import write_heartbeat
from runtime.risk import admit
from runtime.runner.hard_flatten import run_hard_kill
from runtime.tools.kill_drill import command_deadman_check, command_drill_a, command_soft


NOW = datetime(2026, 8, 22, 5, 30, tzinfo=UTC)


def completed(payload):
    return subprocess.CompletedProcess(
        args=["kraken"],
        returncode=0,
        stdout=json.dumps(payload),
        stderr="",
    )


def proposal(**overrides):
    values = {
        "symbol": "PF_XBTUSD",
        "side": "buy",
        "size": "0.001",
        "order_type": "market",
        "notional_usd": "100",
        "leverage": "1",
        "client_order_id": "aura-test-kill",
    }
    values.update(overrides)
    return values


def account_state(**overrides):
    values = {
        "equity": "10000",
        "open_positions_count": 0,
        "daily_pnl": 0,
        "weekly_pnl": 0,
        "kill_state": "armed",
        "as_of": NOW.isoformat().replace("+00:00", "Z"),
    }
    values.update(overrides)
    return values


class KillDrillTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_soft_writes_kill_state_jsonl_and_admit_rejects(self):
        args = Namespace(
            trial_id="T-kill-soft-test",
            aura_root=self.aura_root,
            actor="test:ops",
        )

        result = command_soft(args)

        self.assertTrue(result["ok"])
        self.assertEqual("soft\n", (self.aura_root / "paper" / "kill_state").read_text())
        event = self.read_events("T-kill-soft-test")[0]
        self.assertEqual("aura.kill_event.v1", event["schema"])
        self.assertEqual("set_soft", event["action"])
        self.assertFalse(event["details"]["flatten_existing_positions"])

        admission = admit(proposal(), account_state(kill_state="soft"), now=NOW)
        self.assertFalse(admission.allowed)
        self.assertIn("kill_state soft", admission.reasons)

    def test_hard_cancel_all_and_flattens_buy_and_sell_positions(self):
        positions = {
            "positions": [
                {"symbol": "PF_XBTUSD", "side": "buy", "size": "0.001"},
                {"symbol": "PF_ETHUSD", "side": "sell", "size": "0.002"},
            ]
        }
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            run.side_effect = [
                completed({"cancelled": 2}),
                completed(positions),
                completed({"order_id": "flat-1", "fills": [{"size": "0.001"}]}),
                completed({"order_id": "flat-2", "fills": [{"size": "0.002"}]}),
            ]

            result = run_hard_kill(
                trial_id="T-kill-hard-test",
                aura_root=self.aura_root,
                actor="test:ops",
                kraken_bin="/tmp/kraken",
            )

        self.assertTrue(result.ok)
        self.assertEqual("hard\n", (self.aura_root / "paper" / "kill_state").read_text())
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(["/tmp/kraken", "futures", "paper", "cancel-all", "-o", "json"], commands[0])
        self.assertEqual(["/tmp/kraken", "futures", "paper", "positions", "-o", "json"], commands[1])
        self.assertEqual("sell", commands[2][3])
        self.assertEqual("PF_XBTUSD", commands[2][4])
        self.assertEqual("buy", commands[3][3])
        self.assertEqual("PF_ETHUSD", commands[3][4])
        for command in commands:
            self.assertEqual(["futures", "paper"], command[1:3])
            self.assertNotIn("--allow-dangerous", command)
            self.assertNotIn("live", command)
            self.assertNotIn("funding", command)

        events = self.read_events("T-kill-hard-test")
        self.assertEqual(["set_hard", "cancel_all", "positions_read", "flatten_order", "flatten_order"], [
            event["action"] for event in events
        ])
        self.assertTrue(events[3]["details"]["kill_override"])

    def test_deadman_check_triggers_hard_when_heartbeat_stale(self):
        write_heartbeat(self.aura_root, datetime.now(tz=UTC) - timedelta(seconds=601))
        args = Namespace(
            trial_id="T-kill-deadman-test",
            aura_root=self.aura_root,
            actor="test:ops",
            kraken_bin="/tmp/kraken",
            dead_man_seconds=600,
        )
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            run.side_effect = [
                completed({"cancelled": 0}),
                completed({"positions": []}),
            ]

            result = command_deadman_check(args)

        self.assertTrue(result["ok"])
        self.assertTrue(result["triggered"])
        self.assertEqual("hard\n", (self.aura_root / "paper" / "kill_state").read_text())
        self.assertEqual(2, run.call_count)
        events = self.read_events("T-kill-deadman-test")
        self.assertEqual("deadman_check", events[0]["action"])
        self.assertEqual("set_hard", events[1]["action"])

    def test_deadman_check_does_not_call_kraken_when_heartbeat_fresh(self):
        write_heartbeat(self.aura_root, datetime.now(tz=UTC))
        args = Namespace(
            trial_id="T-kill-deadman-fresh-test",
            aura_root=self.aura_root,
            actor="test:ops",
            kraken_bin="/tmp/kraken",
            dead_man_seconds=600,
        )
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            result = command_deadman_check(args)

        self.assertTrue(result["ok"])
        self.assertFalse(result["triggered"])
        self.assertEqual(0, run.call_count)
        event = self.read_events("T-kill-deadman-fresh-test")[0]
        self.assertFalse(event["details"]["stale"])

    def test_drill_a_rearm_writes_armed_after_soft_reject(self):
        args = Namespace(
            trial_id="T-kill-drill-a-test",
            aura_root=self.aura_root,
            actor="test:ops",
            kraken_bin="/tmp/kraken",
            symbol="PF_XBTUSD",
            size="0.001",
            notional_usd="100",
            rearm=True,
        )
        with patch("runtime.runner.supervised_paper.subprocess.run") as run:
            run.side_effect = [
                completed({"equity": 10_000, "pnl": 0, "weekly_pnl": 0}),
                completed([]),
            ]

            result = command_drill_a(args)

        self.assertTrue(result["ok"])
        self.assertFalse(result["left_soft"])
        self.assertEqual("armed\n", (self.aura_root / "paper" / "kill_state").read_text())
        self.assertEqual(2, run.call_count)
        events = self.read_events("T-kill-drill-a-test")
        self.assertEqual("set_soft", events[0]["action"])
        self.assertEqual("aura.decision_event.v1", events[1]["schema"])
        self.assertEqual("arm", events[2]["action"])

    def read_events(self, trial_id):
        path = self.aura_root / "evidence" / "trials" / trial_id / "decision.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
