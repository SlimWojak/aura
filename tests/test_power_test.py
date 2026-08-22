from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from runtime.eval.power_test import run_power_test
from runtime.market.ohlcv import SOURCE, ohlcv_path, write_candles
from runtime.tools.power_test import main as power_test_main


class PowerTestHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_positive_control_can_clear_track_a_on_tiny_series(self):
        result = run_power_test(
            power_candles(96),
            mode="positive",
            symbol="PF_XBTUSD",
            tf="1h",
            fee_bps=4,
            oos_split=0.7,
            trial_count=37,
            atr_period=14,
            cscv_groups=4,
            output_dir=self.aura_root / "positive",
            regime_tf="4h",
            regime_htf="1d",
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["track_a_keep"])
        self.assertGreater(
            result["selected_trial"]["stats"]["deflated_sharpe_ratio"],
            result["thresholds"]["dsr"],
        )
        self.assertLess(result["matrix"]["pbo"]["pbo"], result["thresholds"]["pbo"])
        self.assertEqual(37, result["matrix"]["pbo"]["n_honest"])
        self.assertEqual(37, result["matrix"]["pbo"]["n_paths"])
        self.assertTrue((self.aura_root / "positive" / "summary.json").exists())

    def test_negative_control_fails_track_a_after_block_shuffle(self):
        result = run_power_test(
            power_candles(96),
            mode="negative",
            symbol="PF_XBTUSD",
            tf="1h",
            fee_bps=4,
            oos_split=0.7,
            trial_count=37,
            atr_period=14,
            cscv_groups=4,
            output_dir=self.aura_root / "negative",
        )

        self.assertTrue(result["ok"])
        self.assertFalse(result["track_a_keep"])
        self.assertLessEqual(
            result["decision_trial"]["stats"]["deflated_sharpe_ratio"],
            result["thresholds"]["dsr"],
        )

    def test_power_test_cli_reads_stored_candles_and_writes_reports(self):
        candles = power_candles(120)
        write_candles(ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root), candles)

        code, output = run_cli(
            [
                "--positive",
                "--aura-root",
                str(self.aura_root),
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
                "--fee-bps",
                "4",
                "--oos-split",
                "0.7",
                "--trial-count",
                "37",
                "--atr-period",
                "14",
                "--cscv-groups",
                "4",
                "--regime-tf",
                "4h",
                "--regime-htf",
                "1d",
            ]
        )

        self.assertEqual(0, code)
        self.assertTrue(output["ok"])
        self.assertTrue(output["track_a_keep"])
        self.assertEqual(120, output["source_candle_count"])
        reports_dir = Path(output["outputs"]["reports_dir"])
        self.assertTrue((reports_dir / "positive-edge" / "report.json").exists())
        self.assertEqual("4h", output["regime_flags"]["regime_tf"])


def power_candles(count: int) -> list[dict[str, str | int]]:
    candles = []
    close = 100.0
    for index in range(count):
        step = ((index % 7) - 3) * 0.2 + (0.05 if index % 2 == 0 else -0.03)
        close = max(1.0, close + step)
        candles.append(
            {
                "schema": "aura.ohlcv_candle.v1",
                "symbol": "PF_XBTUSD",
                "tf": "1h",
                "ts_ms": index * 3_600_000,
                "source": SOURCE,
                "ingested_at": "2026-08-22T00:00:00Z",
                "open": str(close - (step / 2)),
                "high": str(close + 0.5),
                "low": str(close - 0.5),
                "close": str(close),
                "volume": "1",
            }
        )
    return candles


def run_cli(argv: list[str]) -> tuple[int, dict]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = power_test_main(argv)
    return code, json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
