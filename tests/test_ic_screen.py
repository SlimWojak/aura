from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import TestCase

from runtime.eval.ic_screen import build_bar_feature_rows, summarize_kill_rule
from runtime.market.ohlcv import SOURCE, ohlcv_path, write_candles
from runtime.regime.types import RegimeParams
from runtime.tools.eval_run import main as eval_main


FAST_REGIME_PARAMS = RegimeParams(
    tenkan=2,
    kijun=3,
    senkou_b=4,
    displacement=2,
    adx_period=3,
    flat_n=2,
    use_htf_veto=False,
    use_kumo_width_atr=False,
)


class IcScreenTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_chikou_gap_ignores_future_chikou_plot_mutation(self):
        candles = [candle(index, 100 + index * 0.5) for index in range(20)]
        baseline = build_bar_feature_rows(
            candles,
            tf="1h",
            params=FAST_REGIME_PARAMS,
            atr_period=3,
        )
        mutated = list(candles)
        mutated[9] = candle(9, 10_000)

        treatment = build_bar_feature_rows(
            mutated,
            tf="1h",
            params=FAST_REGIME_PARAMS,
            atr_period=3,
        )

        self.assertEqual(baseline[7], treatment[7])
        self.assertEqual(baseline[7]["chikou_gap_atr"], treatment[7]["chikou_gap_atr"])

    def test_kill_rule_marks_both_symbol_zero_cis_dead(self):
        scores = [
            score("PF_XBTUSD", "dead_feature", -0.1, 0.2),
            score("PF_ETHUSD", "dead_feature", -0.3, 0.1),
            score("PF_XBTUSD", "live_feature", 0.1, 0.4),
            score("PF_ETHUSD", "live_feature", -0.2, 0.2),
        ]

        summary = {
            row["feature"]: row
            for row in summarize_kill_rule(scores, symbols=("PF_XBTUSD", "PF_ETHUSD"))
        }

        self.assertEqual("dead", summary["dead_feature"]["verdict"])
        self.assertEqual("survivor", summary["live_feature"]["verdict"])

    def test_ic_screen_cli_writes_json_csv_and_markdown(self):
        write_candles(
            ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root),
            [candle(index, 100 + index * 0.2 + ((index % 24) - 12) * 0.05) for index in range(140)],
        )
        write_candles(
            ohlcv_path("PF_ETHUSD", "1h", aura_root_override=self.aura_root),
            [
                candle(index, 200 + index * 0.15 + ((index % 18) - 9) * 0.04, symbol="PF_ETHUSD")
                for index in range(140)
            ],
        )

        output = run_cli(
            [
                "ic-screen",
                "--aura-root",
                str(self.aura_root),
                "--symbols",
                "PF_XBTUSD,PF_ETHUSD",
                "--tf",
                "1h",
                "--horizons",
                "4,12",
                "--min-count",
                "3",
                "--output-id",
                "ic-screen-test",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertEqual("aura.ic_feature_screen.v1", output["schema"])
        self.assertEqual(["PF_XBTUSD", "PF_ETHUSD"], output["symbols"])
        self.assertGreater(output["scores_count"], 0)
        report_path = Path(output["outputs"]["report_json"])
        scores_path = Path(output["outputs"]["scores_csv"])
        summary_path = Path(output["outputs"]["summary_md"])
        self.assertTrue(report_path.exists())
        self.assertTrue(scores_path.exists())
        self.assertTrue(summary_path.exists())
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIn("Benjamini-Hochberg", saved["multiple_testing_note"])
        self.assertIn("cloud_bias", {row["feature"] for row in saved["scores"]})
        self.assertIn("regime_state", {row["feature"] for row in saved["scores"]})
        self.assertIn("paper-only", summary_path.read_text(encoding="utf-8"))
        self.assertIn("feature", scores_path.read_text(encoding="utf-8").splitlines()[0])

    def test_ic_screen_cli_accepts_enrichment_feature_set(self):
        write_candles(
            ohlcv_path("PF_XBTUSD", "1h", aura_root_override=self.aura_root),
            [candle(index, 100 + index * 0.1 + ((index % 24) - 12) * 0.03) for index in range(200)],
        )
        write_candles(
            ohlcv_path("PF_ETHUSD", "1h", aura_root_override=self.aura_root),
            [
                candle(index, 200 + index * 0.08 + ((index % 18) - 9) * 0.02, symbol="PF_ETHUSD")
                for index in range(200)
            ],
        )

        output = run_cli(
            [
                "ic-screen",
                "--aura-root",
                str(self.aura_root),
                "--symbols",
                "PF_XBTUSD,PF_ETHUSD",
                "--tf",
                "1h",
                "--horizons",
                "4",
                "--min-count",
                "3",
                "--feature-set",
                "enrichment",
                "--output-id",
                "ic-screen-enrichment-test",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertEqual("enrichment", output["feature_set"])
        saved = json.loads(Path(output["outputs"]["report_json"]).read_text(encoding="utf-8"))
        features = {row["feature"] for row in saved["scores"]}
        self.assertIn("daily_dr_side", features)
        self.assertIn("chikou_clears_daily_dr", features)
        self.assertIn("fvg_flat_spanb_overlap", features)


def candle(index: int, close: int | float, *, symbol: str = "PF_XBTUSD") -> dict[str, str | int]:
    return {
        "schema": "aura.ohlcv_candle.v1",
        "symbol": symbol,
        "tf": "1h",
        "ts_ms": index * 3_600_000,
        "source": SOURCE,
        "ingested_at": "2026-08-22T00:00:00Z",
        "open": str(close),
        "high": str(close + 1.0),
        "low": str(close - 1.0),
        "close": str(close),
        "volume": "1",
    }


def score(symbol: str, feature: str, ci_low: float, ci_high: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "tf": "1h",
        "horizon": 4,
        "feature": feature,
        "feature_kind": "continuous",
        "level": None,
        "statistic": "pearson_ic",
        "n": 30,
        "enough_data": True,
        "estimate": (ci_low + ci_high) / 2,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "ci_spans_zero": ci_low <= 0 <= ci_high,
        "bh_q": 0.5,
    }


def run_cli(argv):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = eval_main(argv)
    payload = json.loads(stdout.getvalue())
    if code != 0:
        raise AssertionError(f"eval_run exited {code}: {json.dumps(payload, sort_keys=True)}")
    return payload


if __name__ == "__main__":
    unittest.main()
