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
    compute_efficiency_ratio,
    compute_wilder_adx,
    run_backtest,
    run_backtest_cartridge,
    run_backtest_reference,
    signal_for_closed_bar,
)
from runtime.eval import backtest_ichimoku
from runtime.market.ohlcv import SOURCE, ohlcv_path, write_candles
from runtime.regime import RegimeSnapshot, RegimeState
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

    def test_efficiency_ratio_known_trend_and_chop_values(self):
        trend = [candle(index, 100 + index) for index in range(8)]
        chop_closes = [100, 101, 100, 101, 100, 101, 100, 101]
        chop = [candle(index, close) for index, close in enumerate(chop_closes)]

        trend_er = compute_efficiency_ratio(trend, period=3)
        chop_er = compute_efficiency_ratio(chop, period=3)

        self.assertIsNone(trend_er[2])
        self.assertAlmostEqual(1.0, trend_er[3])
        self.assertAlmostEqual(1.0, trend_er[-1])
        self.assertAlmostEqual(1 / 3, chop_er[3])
        self.assertAlmostEqual(1 / 3, chop_er[-1])

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

    def test_er_cartridge_gate_reduces_or_matches_trade_count(self):
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
                regime={"type": "er", "params": {"period": 3, "threshold": 1.1}}
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(baseline["metrics"]["trade_count"], 0)
        self.assertLessEqual(gated["metrics"]["trade_count"], baseline["metrics"]["trade_count"])
        self.assertIn("entry_gate", gated["signals"][0])

    def test_cloud_thickness_gate_reduces_or_matches_trade_count(self):
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
                regime={"type": "cloud_thickness", "params": {"min_pct": 1000}}
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(baseline["metrics"]["trade_count"], 0)
        self.assertLessEqual(gated["metrics"]["trade_count"], baseline["metrics"]["trade_count"])
        self.assertIn("entry_gate", gated["signals"][0])

    def test_fee_bps_reports_after_fee_pnl_below_raw_pnl(self):
        closes = [100, 100, 100, 101, 102, 103, 104, 103, 102, 101, 100, 99, 98, 97]
        report = run_backtest(
            [candle(index, close) for index, close in enumerate(closes)],
            symbol="PF_XBTUSD",
            tf="1h",
            params=FAST_PARAMS,
            fee_bps=4,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(4, report["fee_bps"])
        self.assertIn("total_pnl_points_after_fees", report["metrics"])
        self.assertLess(
            report["metrics"]["total_pnl_points_after_fees"],
            report["metrics"]["total_pnl_points"],
        )
        self.assertGreater(report["metrics"]["total_fee_points"], 0)

    def test_time_stop_exit_closes_after_max_bars_without_same_bar_reentry(self):
        candles = [candle(index, 100 + index) for index in range(96)]

        report = run_backtest_cartridge(
            candles,
            cartridge=fast_cartridge(
                regime={"type": "none", "params": {}},
                exit_rules={
                    "mode": "time_stop",
                    "close_on_flat": True,
                    "close_on_opposite": True,
                    "max_bars_in_trade": 2,
                },
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        time_stop_trades = [
            trade for trade in report["trades"] if trade["exit_reason"] == "time_stop"
        ]
        self.assertTrue(time_stop_trades)
        first_time_stop_index = report["trades"].index(time_stop_trades[0])
        if first_time_stop_index + 1 < len(report["trades"]):
            next_trade = report["trades"][first_time_stop_index + 1]
            self.assertGreater(next_trade["entry_index"], time_stop_trades[0]["exit_index"])

    def test_long_only_allowed_sides_blocks_short_entries(self):
        closes = [140 - index for index in range(96)]
        entry_rules = {
            "mode": "always_on",
            "allowed_sides": ["long"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "tenkan_over_kijun_for_long_under_for_short",
            "require_chikou_confirmation": True,
            "chikou_mode": "close",
        }

        report = run_backtest_cartridge(
            [candle(index, close) for index, close in enumerate(closes)],
            cartridge=fast_cartridge(
                regime={"type": "none", "params": {}},
                entry_rules=entry_rules,
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        denied_short_signals = [
            signal
            for signal in report["signals"]
            if signal["bias"] == "short" and signal["entry_gate"]["reason"] == "side_not_allowed"
        ]
        self.assertTrue(denied_short_signals)
        self.assertEqual(0, report["metrics"]["trade_count"])
        self.assertGreater(report["metrics"]["entry_gate_denied_count"], 0)

    def test_tk_cloud_strong_detects_cross_and_filters_weak_cloud(self):
        strong_closes = [100, 100, 100, 100, 98, 96, 94, 92, 90, 110, 120, 130, 140, 150]
        weak_closes = [100, 120, 120, 120, 118, 116, 114, 112, 110, 112, 114, 116, 118]
        strong = run_backtest_cartridge(
            [candle(index, close) for index, close in enumerate(strong_closes)],
            cartridge=tk_cloud_strong_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )
        weak = run_backtest_cartridge(
            [candle(index, close) for index, close in enumerate(weak_closes)],
            cartridge=tk_cloud_strong_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(strong["metrics"]["trade_count"], 0)
        self.assertEqual(0, weak["metrics"]["trade_count"])
        self.assertIn("long", {trade["direction"] for trade in strong["trades"]})

    def test_plain_tk_cross_uses_close_vs_cloud_without_both_lines_outside(self):
        closes = [140, 140, 140, 90, 110, 121, 122, 123]
        candles = [candle(index, close) for index, close in enumerate(closes)]

        plain = run_backtest_cartridge(
            candles,
            cartridge=tk_cross_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )
        strong = run_backtest_cartridge(
            candles,
            cartridge=tk_cloud_strong_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(plain["metrics"]["trade_count"], 0)
        self.assertEqual(0, strong["metrics"]["trade_count"])
        long_signal = next(signal for signal in plain["signals"] if signal["bias"] == "long")
        self.assertTrue(long_signal["features"]["tk_bull_cross"])
        self.assertTrue(long_signal["features"]["close_above_cloud"])

    def test_tk_strong_refinement_filters_reduce_or_match_parent_trades(self):
        closes = [100, 100, 100, 100, 98, 96, 94, 92, 90, 110, 120, 130, 140, 150]
        candles = [candle(index, close) for index, close in enumerate(closes)]
        parent = run_backtest_cartridge(
            candles,
            cartridge=tk_cloud_strong_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )
        kijun_dip = run_backtest_cartridge(
            candles,
            cartridge=tk_cloud_strong_cartridge(
                entry_rule_overrides={"require_kijun_dip_setup": True, "setup_bars": 8}
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )
        cloud_color = run_backtest_cartridge(
            candles,
            cartridge=tk_cloud_strong_cartridge(
                entry_rule_overrides={"require_cloud_color_align": True}
            ),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(parent["metrics"]["trade_count"], 0)
        self.assertLessEqual(kijun_dip["metrics"]["trade_count"], parent["metrics"]["trade_count"])
        self.assertLessEqual(cloud_color["metrics"]["trade_count"], parent["metrics"]["trade_count"])
        self.assertTrue(
            any(
                signal["features"].get("require_kijun_dip_setup")
                for signal in kijun_dip["signals"]
                if signal["ok"]
            )
        )
        self.assertTrue(
            any(
                signal["features"].get("require_cloud_color_align")
                for signal in cloud_color["signals"]
                if signal["ok"]
            )
        )

    def test_phase2_regime_gate_reduces_entries_when_regime_denies(self):
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

        with patch.object(
            backtest_ichimoku,
            "classify_series",
            return_value=regime_snapshots(len(candles), RegimeState.RANGE),
        ):
            gated = run_backtest_cartridge(
                candles,
                cartridge=fast_cartridge(regime={"type": "none", "params": {}}),
                symbol="PF_XBTUSD",
                tf="1h",
                regime_tf="1h",
                regime_htf=None,
            )

        self.assertGreater(baseline["metrics"]["trade_count"], 0)
        self.assertEqual(0, gated["metrics"]["trade_count"])
        self.assertGreater(gated["metrics"]["entry_gate_denied_count"], 0)
        self.assertTrue(
            any(signal["entry_gate"]["reason"] == "regime_veto" for signal in gated["signals"])
        )

    def test_regime_exit_flattens_when_open_side_no_longer_allowed(self):
        candles = [candle(index, 100 + index) for index in range(96)]
        states = [
            RegimeState.TREND_BULL if index < 48 else RegimeState.RANGE
            for index in range(len(candles))
        ]

        with patch.object(
            backtest_ichimoku,
            "classify_series",
            return_value=regime_snapshots_by_state(states),
        ):
            report = run_backtest_cartridge(
                candles,
                cartridge=fast_cartridge(
                    regime={"type": "none", "params": {}},
                    exit_rules={
                        "mode": "regime_exit",
                        "close_on_flat": True,
                        "close_on_opposite": True,
                        "max_bars_in_trade": None,
                    },
                ),
                symbol="PF_XBTUSD",
                tf="1h",
                regime_tf="1h",
                regime_htf=None,
            )

        self.assertTrue(
            any(trade["exit_reason"] == "regime_exit" for trade in report["trades"])
        )
        self.assertTrue(
            any(
                signal.get("exit_gate", {}).get("reason") == "regime_veto"
                for signal in report["signals"]
            )
        )

    def test_oos_baseline_ref_loads_ichi_v0_baseline_with_same_regime_gate(self):
        closes = [100 + ((index % 24) - 12) + index * 0.1 for index in range(180)]
        candles = [candle(index, close) for index, close in enumerate(closes)]
        cartridge = fast_cartridge(
            regime={"type": "none", "params": {}},
            baseline_ref="ichi_v0_baseline",
        )

        def classify_side_effect(regime_candles, params, tf, htf_candles=None):
            return regime_snapshots(len(regime_candles), RegimeState.TREND_BULL)

        with patch.object(
            backtest_ichimoku,
            "classify_series",
            side_effect=classify_side_effect,
        ) as classify_mock:
            report = backtest_ichimoku.run_cartridge_oos_split(
                candles,
                cartridge=cartridge,
                symbol="PF_XBTUSD",
                tf="1h",
                fee_bps=4,
                regime_tf="1h",
                regime_htf=None,
                oos_split=0.5,
            )

        self.assertTrue(report["ok"])
        self.assertEqual(4, classify_mock.call_count)
        self.assertEqual("ichi_v0_baseline", report["baseline"]["ref"])
        self.assertEqual("ichi_v0_baseline", report["baseline"]["is"]["cartridge"]["id"])
        self.assertEqual(4, report["baseline"]["is"]["fee_bps"])
        self.assertIn("regime_gate", report["baseline"]["is"])

    def test_phase2_regime_gate_side_locks_trend_states(self):
        closes = [140 - index for index in range(96)]
        candles = [candle(index, close) for index, close in enumerate(closes)]

        with patch.object(
            backtest_ichimoku,
            "classify_series",
            return_value=regime_snapshots(len(candles), RegimeState.TREND_BULL),
        ):
            gated = run_backtest_cartridge(
                candles,
                cartridge=fast_cartridge(regime={"type": "none", "params": {}}),
                symbol="PF_XBTUSD",
                tf="1h",
                regime_tf="1h",
                regime_htf=None,
            )

        self.assertEqual(0, gated["metrics"]["trade_count"])
        denied_signals = [
            signal
            for signal in gated["signals"]
            if signal["bias"] == "short" and not signal["entry_gate"]["allowed"]
        ]
        self.assertTrue(denied_signals)
        self.assertEqual("TREND_BULL", denied_signals[0]["entry_gate"]["values"]["state"])

    def test_trend_only_cartridge_requires_regime_flag(self):
        cartridge = tk_cloud_strong_cartridge()
        cartridge["id"] = "ichi_tk_strong_trend_only_v0"

        with self.assertRaisesRegex(ValueError, "requires --regime-tf"):
            run_backtest_cartridge(
                [candle(index, 100 + index) for index in range(96)],
                cartridge=cartridge,
                symbol="PF_XBTUSD",
                tf="1h",
            )

    def test_new_trend_family_cartridge_requires_regime_flag(self):
        cartridges = [
            ("ichi_tk_cross_trend_v0", tk_cross_cartridge()),
            ("ichi_params_20_60_trend_eth_dd_v0", fast_cartridge(regime={"type": "none", "params": {}})),
            ("ichi_params_10_30_trend_v0", fast_cartridge(regime={"type": "none", "params": {}})),
            ("ichi_tenkan_bounce_trend_v0", tenkan_bounce_cartridge()),
        ]

        for cartridge_id, cartridge in cartridges:
            with self.subTest(cartridge_id=cartridge_id):
                cartridge["id"] = cartridge_id

                with self.assertRaisesRegex(ValueError, "requires --regime-tf"):
                    run_backtest_cartridge(
                        [candle(index, 100 + index) for index in range(96)],
                        cartridge=cartridge,
                        symbol="PF_XBTUSD",
                        tf="1h",
                    )

    def test_kijun_bounce_cartridge_detects_cross_back_entry(self):
        closes = [100, 100, 100, 100, 98, 96, 94, 92, 90, 100, 110, 120, 130, 140]
        report = run_backtest_cartridge(
            [candle(index, close) for index, close in enumerate(closes)],
            cartridge=kijun_bounce_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(report["metrics"]["trade_count"], 0)
        self.assertIn("long", {trade["direction"] for trade in report["trades"]})
        long_signals = [signal for signal in report["signals"] if signal["bias"] == "long"]
        self.assertTrue(long_signals)

    def test_tenkan_bounce_cartridge_detects_tenkan_reclaim_entry(self):
        closes = [100, 100, 100, 100, 98, 96, 94, 92, 90, 100, 110, 120, 130, 140]
        report = run_backtest_cartridge(
            [candle(index, close) for index, close in enumerate(closes)],
            cartridge=tenkan_bounce_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(report["metrics"]["trade_count"], 0)
        self.assertIn("long", {trade["direction"] for trade in report["trades"]})
        long_signal = next(signal for signal in report["signals"] if signal["bias"] == "long")
        self.assertTrue(long_signal["features"]["close_crossed_above_tenkan"])
        self.assertTrue(long_signal["features"]["close_above_cloud"])
        self.assertIn("tenkan", long_signal["components"])
        self.assertNotIn("kijun", long_signal["components"])

    def test_kumo_break_cartridge_detects_close_through_cloud(self):
        closes = [140, 140, 140, 140, 90, 110, 121, 122]
        report = run_backtest_cartridge(
            [candle(index, close) for index, close in enumerate(closes)],
            cartridge=kumo_break_cartridge(),
            symbol="PF_XBTUSD",
            tf="1h",
        )

        self.assertGreater(report["metrics"]["trade_count"], 0)
        self.assertIn("long", {trade["direction"] for trade in report["trades"]})
        long_signal = next(signal for signal in report["signals"] if signal["bias"] == "long")
        self.assertTrue(long_signal["features"]["previous_close_at_or_below_cloud_top"])
        self.assertTrue(long_signal["features"]["close_above_cloud"])

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

    def test_cartridge_cli_oos_split_report_contains_both_halves(self):
        candles = [candle(index, 100 + ((index % 24) - 12) + index * 0.1) for index in range(300)]
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
                "--fee-bps",
                "4",
                "--oos-split",
                "0.7",
                "--metrics-only",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertEqual(210, output["oos_split"]["is_candle_count"])
        self.assertEqual(90, output["oos_split"]["oos_candle_count"])
        self.assertIn("pass_oos_gate", output["oos_split"])
        self.assertIn("metrics", output["is"])
        self.assertIn("metrics", output["oos"])
        self.assertIn("metrics", output["baseline"]["is"])
        self.assertNotIn("signals", output["is"])
        saved = json.loads(Path(output["outputs"]["report_json"]).read_text(encoding="utf-8"))
        self.assertIn("signals", saved["is"])
        self.assertIn("signals", saved["oos"])

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
        self.assertIn("ichi_er_regime_v0", output["runnable_cartridges"])
        self.assertIn("ichi_tk_cloud_strong_v0", output["runnable_cartridges"])
        self.assertNotIn("ichi_adx_regime_v0", output["runnable_cartridges"])
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


def fast_cartridge(
    *,
    regime: dict,
    baseline_ref: str = "ichimoku_v0",
    entry_rules: dict | None = None,
    exit_rules: dict | None = None,
) -> dict:
    return {
        "id": "test_fast_cartridge",
        "title": "Test fast cartridge",
        "status": "queued",
        "thesis": "Test cartridge",
        "symbol": "PF_XBTUSD",
        "tf": "1h",
        "baseline_ref": baseline_ref,
        "ichimoku": {
            "tenkan": FAST_PARAMS.tenkan,
            "kijun": FAST_PARAMS.kijun,
            "senkou_b": FAST_PARAMS.senkou_b,
            "displacement": FAST_PARAMS.displacement,
        },
        "entry_rules": entry_rules or {
            "mode": "always_on",
            "allowed_sides": ["long", "short"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "tenkan_over_kijun_for_long_under_for_short",
            "require_chikou_confirmation": True,
            "chikou_mode": "close",
        },
        "exit_rules": exit_rules or {
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


def tk_cloud_strong_cartridge(entry_rule_overrides: dict | None = None) -> dict:
    entry_rules = {
        "mode": "tk_cloud_bias",
        "allowed_sides": ["long", "short"],
        "require_close_vs_cloud": "above_for_long_below_for_short",
        "require_tk_state": "tk_cross_only",
        "require_chikou_confirmation": False,
        "chikou_mode": "close",
    }
    if entry_rule_overrides:
        entry_rules.update(entry_rule_overrides)
    return fast_cartridge(
        regime={"type": "none", "params": {}},
        entry_rules=entry_rules,
        exit_rules={
            "mode": "flat_on_rule_fail",
            "close_on_flat": True,
            "close_on_opposite": True,
            "max_bars_in_trade": None,
        },
    )


def tk_cross_cartridge() -> dict:
    return fast_cartridge(
        regime={"type": "none", "params": {}},
        entry_rules={
            "mode": "tk_cross",
            "allowed_sides": ["long", "short"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "tk_cross_only",
            "require_chikou_confirmation": False,
            "chikou_mode": "close",
        },
        exit_rules={
            "mode": "flat_on_rule_fail",
            "close_on_flat": True,
            "close_on_opposite": True,
            "max_bars_in_trade": None,
        },
    )


def kumo_break_cartridge() -> dict:
    return fast_cartridge(
        regime={"type": "none", "params": {}},
        entry_rules={
            "mode": "kumo_break",
            "allowed_sides": ["long", "short"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "none",
            "require_chikou_confirmation": False,
            "chikou_mode": "close",
        },
        exit_rules={
            "mode": "flat_on_rule_fail",
            "close_on_flat": True,
            "close_on_opposite": True,
            "max_bars_in_trade": None,
        },
    )


def kijun_bounce_cartridge() -> dict:
    return fast_cartridge(
        regime={"type": "none", "params": {}},
        entry_rules={
            "mode": "kijun_bounce",
            "allowed_sides": ["long", "short"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "none",
            "require_chikou_confirmation": True,
            "chikou_mode": "close",
        },
        exit_rules={
            "mode": "flat_on_rule_fail",
            "close_on_flat": True,
            "close_on_opposite": True,
            "max_bars_in_trade": None,
        },
    )


def tenkan_bounce_cartridge() -> dict:
    return fast_cartridge(
        regime={"type": "none", "params": {}},
        entry_rules={
            "mode": "tenkan_bounce",
            "allowed_sides": ["long", "short"],
            "require_close_vs_cloud": "above_for_long_below_for_short",
            "require_tk_state": "none",
            "require_chikou_confirmation": False,
            "chikou_mode": "close",
        },
        exit_rules={
            "mode": "flat_on_rule_fail",
            "close_on_flat": True,
            "close_on_opposite": True,
            "max_bars_in_trade": None,
        },
    )


def regime_snapshots(count: int, state: RegimeState) -> list[RegimeSnapshot]:
    return [
        RegimeSnapshot(
            state=state,
            confidence=0.9,
            reasons=("test_fixture",),
            features={},
            as_of=index * 3_600_000,
            tf="1h",
        )
        for index in range(count)
    ]


def regime_snapshots_by_state(states: list[RegimeState]) -> list[RegimeSnapshot]:
    return [
        RegimeSnapshot(
            state=state,
            confidence=0.9,
            reasons=("test_fixture",),
            features={},
            as_of=index * 3_600_000,
            tf="1h",
        )
        for index, state in enumerate(states)
    ]


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
