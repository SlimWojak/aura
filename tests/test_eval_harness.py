from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import TestCase

from runtime.brain.types import IchimokuParams
from runtime.eval import run_backtest, signal_for_closed_bar
from runtime.market.ohlcv import SOURCE, ohlcv_path, write_candles
from runtime.tools.eval_run import main as eval_main


FAST_PARAMS = IchimokuParams(tenkan=2, kijun=3, senkou_b=4, displacement=2)


class EvalHarnessTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_backtest_scores_known_long_flat_short_transitions(self):
        closes = [100, 100, 100, 101, 102, 103, 104, 103, 102, 101, 100, 99, 98, 97]
        report = run_backtest(
            [candle(index, close) for index, close in enumerate(closes)],
            symbol="PF_XBTUSD",
            tf="1h",
            params=FAST_PARAMS,
        )

        self.assertTrue(report["ok"])
        self.assertEqual("aura.backtest_report.v1", report["schema"])
        self.assertEqual(2, report["metrics"]["trade_count"])
        self.assertGreater(report["metrics"]["total_pnl_points"], 0)
        self.assertEqual("short", report["metrics"]["final_bias"])
        self.assertIn("long", [signal["bias"] for signal in report["signals"]])
        self.assertIn("flat", [signal["bias"] for signal in report["signals"]])
        self.assertIn("short", [signal["bias"] for signal in report["signals"]])
        self.assertEqual("next_open", report["trades"][0]["entry_basis"])

    def test_signal_for_closed_bar_ignores_future_candle_mutation(self):
        candles = [candle(index, 100 + index) for index in range(12)]
        baseline = signal_for_closed_bar(candles, index=7, params=FAST_PARAMS).to_dict()
        mutated = list(candles)
        mutated[10] = candle(10, 10_000)

        treatment = signal_for_closed_bar(mutated, index=7, params=FAST_PARAMS).to_dict()

        self.assertEqual(baseline, treatment)

    def test_backtest_cli_writes_eval_report(self):
        candles = [candle(index, 100 + index) for index in range(90)]
        write_candles(ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root), candles)

        output = run_cli(
            [
                "backtest",
                "--aura-root",
                str(self.aura_root),
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
            ]
        )

        self.assertTrue(output["ok"])
        report_path = Path(output["outputs"]["report_json"])
        trades_path = Path(output["outputs"]["trades_jsonl"])
        self.assertTrue(report_path.exists())
        self.assertTrue(trades_path.exists())
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(output["eval_id"], saved["eval_id"])

    def test_ledger_summarizes_temp_evidence_dir(self):
        trial_root = self.aura_root / "evidence" / "trials" / "T-ledger"
        trial_root.mkdir(parents=True)
        events = [
            {
                "schema": "aura.brain_signal.v1",
                "intent": "brain_signal",
                "signal": {"bias": "long"},
            },
            {
                "schema": "aura.decision_event.v1",
                "intent": "open",
                "risk_gate": {"result": "allow"},
                "fills": [{"price": "100", "size": "1"}],
                "pnl_delta_paper": None,
            },
        ]
        with (trial_root / "decision.jsonl").open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True))
                handle.write("\n")

        output = run_cli(["ledger", "--aura-root", str(self.aura_root)])

        self.assertTrue(output["ok"])
        self.assertEqual(1, output["trials_scanned"])
        self.assertEqual(2, output["event_count"])
        self.assertEqual(1, output["counts"]["by_bias"]["long"])
        self.assertEqual(1, output["counts"]["by_risk_result"]["allow"])
        self.assertEqual(1, output["paper"]["fill_price_count"])
        self.assertNotIn("realized_pnl_paper", output["paper"])
        self.assertTrue(Path(output["output_path"]).exists())


def candle(index: int, close: int | float) -> dict[str, str | int]:
    return {
        "schema": "aura.ohlcv_candle.v1",
        "symbol": "PF_XBTUSD",
        "tf": "1h",
        "ts_ms": index * 3_600_000,
        "source": SOURCE,
        "ingested_at": "2026-08-22T00:00:00Z",
        "open": str(close),
        "high": str(close + 0.1),
        "low": str(close - 0.1),
        "close": str(close),
        "volume": "1",
    }


def run_cli(argv):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = eval_main(argv)
    if code != 0:
        raise AssertionError(f"eval_run exited {code}: {stdout.getvalue()}")
    return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
