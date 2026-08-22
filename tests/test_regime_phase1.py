from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import TestCase

from runtime.market.ohlcv import SOURCE, ohlcv_path, write_candles
from runtime.regime import RegimeParams, RegimeState, build_feature_series, classify_series
from runtime.regime.features import price_vs_kumo
from runtime.tools.regime_label import main as regime_main


FAST_PARAMS = RegimeParams(
    tenkan=2,
    kijun=3,
    senkou_b=4,
    displacement=2,
    adx_period=3,
    adx_weak=20,
    adx_strong=25,
    thin_kumo_atr=0.1,
    flat_n=3,
    flat_atr_fraction=0.05,
    dwell_bars=3,
)


class RegimePhase1Tests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_state_contract_is_exactly_five_labels(self):
        self.assertEqual(
            {
                "TREND_BULL",
                "TREND_BEAR",
                "TRANSITION",
                "RANGE",
                "VOLATILE",
            },
            {state.value for state in RegimeState},
        )

    def test_known_strong_uptrend_reaches_trend_bull_after_dwell(self):
        snapshots = classify_series(
            [candle(index, 100 + index) for index in range(30)],
            params=FAST_PARAMS,
            tf="4h",
        )

        self.assertEqual(RegimeState.TREND_BULL, snapshots[-1].state)
        self.assertEqual(("full_bull_stack",), snapshots[-1].reasons)
        self.assertGreaterEqual(snapshots[-1].features["adx"], FAST_PARAMS.adx_strong)
        self.assertTrue(snapshots[-1].features["di_bullish"])

    def test_inside_cloud_box_is_range(self):
        snapshots = classify_series(
            [candle(index, 100, high=101, low=99) for index in range(30)],
            params=FAST_PARAMS,
            tf="4h",
        )

        self.assertEqual(RegimeState.RANGE, snapshots[-1].state)
        self.assertEqual("inside", snapshots[-1].features["price_vs_kumo"])

    def test_outside_cloud_with_low_adx_is_volatile(self):
        volatile_params = RegimeParams(
            tenkan=2,
            kijun=3,
            senkou_b=4,
            displacement=2,
            adx_period=3,
            adx_weak=20,
            adx_strong=101,
            thin_kumo_atr=0.1,
            flat_n=3,
            flat_atr_fraction=0.05,
            dwell_bars=1,
        )
        candles = [candle(index, 100, high=101, low=99) for index in range(25)]
        candles.extend(candle(index, 104, high=105, low=103) for index in range(25, 28))

        snapshots = classify_series(candles, params=volatile_params, tf="4h")

        self.assertEqual(RegimeState.VOLATILE, snapshots[-1].state)
        self.assertEqual("above", snapshots[-1].features["price_vs_kumo"])
        self.assertLess(snapshots[-1].features["adx"], volatile_params.adx_strong)

    def test_thin_cloud_chop_is_range(self):
        thin_params = RegimeParams(
            tenkan=2,
            kijun=3,
            senkou_b=4,
            displacement=2,
            adx_period=3,
            adx_weak=20,
            adx_strong=25,
            thin_kumo_atr=999,
            flat_n=3,
            flat_atr_fraction=0.05,
            dwell_bars=1,
        )

        snapshots = classify_series(
            [candle(index, 100 + ((index % 2) * 0.05), high=101, low=99) for index in range(30)],
            params=thin_params,
            tf="4h",
        )

        self.assertEqual(RegimeState.RANGE, snapshots[-1].state)
        self.assertTrue(snapshots[-1].features["thin_kumo"])

    def test_hysteresis_keeps_trend_through_one_bar_adx_dip(self):
        params = RegimeParams(
            tenkan=2,
            kijun=3,
            senkou_b=4,
            displacement=2,
            adx_period=3,
            adx_weak=20,
            adx_strong=90,
            thin_kumo_atr=0.1,
            flat_n=3,
            flat_atr_fraction=0.05,
            dwell_bars=3,
        )
        candles = [candle(index, 100 + index) for index in range(25)]
        candles.append(candle(25, 123))

        snapshots = classify_series(candles, params=params, tf="4h")

        self.assertEqual(RegimeState.TREND_BULL, snapshots[-1].state)
        self.assertLess(snapshots[-1].features["adx"], params.adx_strong)
        self.assertEqual("VOLATILE", snapshots[-1].features["dwell_pending_state"])
        self.assertIn("dwell_pending:VOLATILE:1", snapshots[-1].reasons)

    def test_ablation_switches_can_remove_adx_di_and_width_requirements(self):
        restrictive_params = RegimeParams(
            tenkan=2,
            kijun=3,
            senkou_b=4,
            displacement=2,
            adx_period=3,
            adx_weak=20,
            adx_strong=101,
            thin_kumo_atr=999,
            flat_n=3,
            flat_atr_fraction=0.05,
            dwell_bars=1,
        )
        candles = [candle(index, 100 + index) for index in range(30)]

        full = classify_series(candles, params=restrictive_params, tf="4h")
        ablated = classify_series(
            candles,
            params=replace(
                restrictive_params,
                use_adx_di=False,
                use_kumo_width_atr=False,
            ),
            tf="4h",
        )

        self.assertNotEqual(RegimeState.TREND_BULL, full[-1].state)
        self.assertEqual(RegimeState.TREND_BULL, ablated[-1].state)

    def test_ablation_switch_can_remove_dwell_hysteresis(self):
        params = RegimeParams(
            tenkan=2,
            kijun=3,
            senkou_b=4,
            displacement=2,
            adx_period=3,
            adx_weak=20,
            adx_strong=90,
            thin_kumo_atr=0.1,
            flat_n=3,
            flat_atr_fraction=0.05,
            dwell_bars=3,
        )
        candles = [candle(index, 100 + index) for index in range(25)]
        candles.append(candle(25, 123))

        snapshots = classify_series(
            candles,
            params=replace(params, use_dwell=False),
            tf="4h",
        )

        self.assertEqual(RegimeState.VOLATILE, snapshots[-1].state)
        self.assertNotIn("dwell_pending_state", snapshots[-1].features)

    def test_price_vs_kumo_uses_displaced_cloud_not_undisplaced_raw_spans(self):
        params = RegimeParams(
            tenkan=2,
            kijun=3,
            senkou_b=4,
            displacement=5,
            adx_period=3,
            adx_weak=20,
            adx_strong=25,
            thin_kumo_atr=0.1,
            flat_n=3,
            flat_atr_fraction=0.05,
            dwell_bars=1,
        )
        candles = [candle(index, 100, high=101, low=99) for index in range(8)]
        candles.extend(candle(index, 50, high=51, low=49) for index in range(8, 12))
        candles.append(candle(12, 60, high=61, low=59))
        series = build_feature_series(candles, params=params)
        point = series.ichimoku.points[-1]
        raw_top = max(point.senkou_span_a_raw, point.senkou_span_b_raw)

        self.assertEqual("below", price_vs_kumo(point))
        self.assertGreater(point.close, raw_top)

    def test_cli_label_writes_jsonl_and_summary_without_htf(self):
        source = [candle(index, 100 + index, tf="1h", ts_ms=index * 3_600_000) for index in range(360)]
        write_candles(ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root), source)

        output = run_cli(
            [
                "label",
                "--aura-root",
                str(self.aura_root),
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "4h",
                "--htf",
                "none",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertIn("occupancy_pct", output["summary"])
        self.assertIn("flip_rate", output["summary"])
        labels_path = Path(output["outputs"]["labels_jsonl"])
        summary_path = Path(output["outputs"]["summary_json"])
        self.assertTrue(labels_path.exists())
        self.assertTrue(summary_path.exists())
        first_label = json.loads(labels_path.read_text(encoding="utf-8").splitlines()[0])
        saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual("aura.regime_label.v1", first_label["schema"])
        self.assertEqual("aura.regime_summary.v1", saved_summary["schema"])


def candle(
    index: int,
    close: int | float,
    *,
    high: int | float | None = None,
    low: int | float | None = None,
    tf: str = "4h",
    ts_ms: int | None = None,
) -> dict[str, str | int]:
    resolved_high = close + 1 if high is None else high
    resolved_low = close - 1 if low is None else low
    return {
        "schema": "aura.ohlcv_candle.v1",
        "symbol": "PF_XBTUSD",
        "tf": tf,
        "ts_ms": index * 14_400_000 if ts_ms is None else ts_ms,
        "source": SOURCE,
        "ingested_at": "2026-08-22T00:00:00Z",
        "open": str(close),
        "high": str(resolved_high),
        "low": str(resolved_low),
        "close": str(close),
        "volume": "1",
    }


def run_cli(argv):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = regime_main(argv)
    if code != 0:
        raise AssertionError(f"regime_label exited {code}: {stdout.getvalue()}")
    return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
