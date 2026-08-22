from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import TestCase
from unittest.mock import patch

from runtime.brain.types import IchimokuParams
from runtime.eval import (
    compute_wilder_adx,
    run_backtest,
    run_backtest_cartridge,
    run_backtest_reference,
    signal_for_closed_bar,
)
from runtime.eval import backtest_ichimoku
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

    def test_fast_backtest_matches_reference_metrics_trades_and_signals(self):
        closes = [
            100 + ((index % 16) - 8) + (index * 0.03)
            for index in range(96)
        ]
        candles = [candle(index, close) for index, close in enumerate(closes)]

        fast = run_backtest(candles, symbol="PF_XBTUSD", tf="1h", params=FAST_PARAMS)
        reference = run_backtest_reference(
            candles,
            symbol="PF_XBTUSD",
            tf="1h",
            params=FAST_PARAMS,
        )

        self.assertEqual("precomputed_ichimoku_series_v1", fast["engine"])
        self.assertEqual("reference_slice_recompute_v1", reference["engine"])
        self.assertEqual(reference["metrics"], fast["metrics"])
        self.assertEqual(reference["trades"], fast["trades"])
        self.assertEqual(reference["signals"], fast["signals"])

    def test_fast_backtest_computes_ichimoku_once_for_large_series(self):
        candles = [
            candle(index, 100 + ((index % 48) - 24) * 0.25)
            for index in range(6_000)
        ]

        with patch.object(
            backtest_ichimoku,
            "compute_ichimoku",
            wraps=backtest_ichimoku.compute_ichimoku,
        ) as wrapped_compute:
            report = run_backtest(candles, symbol="PF_XBTUSD", tf="1h", params=FAST_PARAMS)

        self.assertTrue(report["ok"])
        self.assertEqual(1, wrapped_compute.call_count)
        self.assertEqual(6_000 - FAST_PARAMS.minimum_candles + 1, report["evaluated_bars"])

    def test_wilder_adx_known_trend_and_flat_values(self):
        trend = [candle(index, 100 + index) for index in range(12)]
        flat = [candle(index, 100) for index in range(12)]

        trend_adx = compute_wilder_adx(trend, period=3)
        flat_adx = compute_wilder_adx(flat, period=3)

        self.assertIsNone(trend_adx[4])
        self.assertAlmostEqual(100.0, trend_adx[5])
        self.assertAlmostEqual(100.0, trend_adx[-1])
        self.assertAlmostEqual(0.0, flat_adx[5])
        self.assertAlmostEqual(0.0, flat_adx[-1])

    def test_adx_cartridge_gate_reduces_or_matches_trade_count(self):
        closes = [
            100 + ((index % 16) - 8) + (index * 0.03)
            for index in range(96)
        ]
        candles = [candle(index, close) for index, close in enumerate(closes)]
        baseline = run_backtest_cartridge(
            candles,
            cartridge=fast_cartridge(regime={"type": "none", "params": {}}),
            symbol="PF_XBTUSD",
            tf="1h",
        )
        gated = run_backtest_cartridge(
            candles,
            cartridge=fast_cartridge(
                regime={"type": "adx", "params": {"period": 3, "threshold": 101}}
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(baseline["metrics"]["trade_count"], 0)
        self.assertLessEqual(gated["metrics"]["trade_count"], baseline["metrics"]["trade_count"])
        self.assertEqual("precomputed_ichimoku_cartridge_v1", gated["engine"])
        self.assertIn("entry_gate", gated["signals"][0])

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

    def test_backtest_cli_metrics_only_keeps_stdout_compact_and_windows(self):
        candles = [candle(index, 100 + index) for index in range(120)]
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
                "--since",
                "1970-01-01T10:00:00Z",
                "--max-bars",
                "80",
                "--metrics-only",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertEqual(120, output["source_candle_count"])
        self.assertEqual(80, output["candle_count"])
        self.assertEqual(40 * 3_600_000, output["window"]["first_ts_ms"])
        self.assertIn("metrics", output)
        self.assertNotIn("trades", output)
        self.assertNotIn("signals", output)
        saved = json.loads(Path(output["outputs"]["report_json"]).read_text(encoding="utf-8"))
        self.assertIn("trades", saved)
        self.assertIn("signals", saved)

    def test_cartridge_cli_metrics_only_runs_seed_baseline(self):
        candles = [candle(index, 100 + index) for index in range(90)]
        write_candles(ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root), candles)

        output = run_cli(
            [
                "cartridge",
                "--aura-root",
                str(self.aura_root),
                "--id",
                "ichi_v0_baseline",
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
                "--metrics-only",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertEqual("ichi_v0_baseline", output["cartridge"]["id"])
        self.assertNotIn("trades", output)
        self.assertTrue(Path(output["outputs"]["report_json"]).exists())

    def test_cartridge_cli_lists_runnable_ids_for_unwired_tk_cloud_seed(self):
        candles = [candle(index, 100 + index) for index in range(90)]
        write_candles(ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root), candles)

        code, output = run_cli_result(
            [
                "cartridge",
                "--aura-root",
                str(self.aura_root),
                "--id",
                "ichi_tk_cloud_v0",
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
                "--metrics-only",
            ]
        )

        self.assertEqual(1, code)
        self.assertFalse(output["ok"])
        self.assertIn("not runnable", output["error"])
        self.assertIn("ichi_adx_regime_v0", output["runnable_cartridges"])
        self.assertNotIn("ichi_tk_cloud_v0", output["runnable_cartridges"])

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


def fast_cartridge(*, regime: dict) -> dict:
    return {
        "id": "test_fast_cartridge",
        "title": "Test fast cartridge",
        "status": "queued",
        "thesis": "Test cartridge",
        "symbol": "PF_XBTUSD",
        "tf": "1h",
        "baseline_ref": "ichimoku_v0",
        "ichimoku": {
            "tenkan": FAST_PARAMS.tenkan,
            "kijun": FAST_PARAMS.kijun,
            "senkou_b": FAST_PARAMS.senkou_b,
            "displacement": FAST_PARAMS.displacement,
        },
        "entry_rules": {
            "mode": "always_on",
            "allowed_sides": ["long", "short"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "tenkan_over_kijun_for_long_under_for_short",
            "require_chikou_confirmation": True,
            "chikou_mode": "close",
        },
        "exit_rules": {
            "mode": "bias_flip",
            "close_on_flat": True,
            "close_on_opposite": True,
            "max_bars_in_trade": None,
        },
        "regime": regime,
        "kill_criteria": {
            "max_dd_points": 100,
            "min_trades": 1,
            "must_beat_baseline": False,
            "baseline_metric": "total_pnl_points",
            "notes": "Test only.",
        },
        "sources": ["tests/test_eval_harness.py"],
    }


def run_cli(argv):
    code, output = run_cli_result(argv)
    if code != 0:
        raise AssertionError(f"eval_run exited {code}: {json.dumps(output, sort_keys=True)}")
    return output


def run_cli_result(argv):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = eval_main(argv)
    return code, json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
