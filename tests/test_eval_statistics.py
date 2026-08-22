from __future__ import annotations

import unittest

from runtime.eval import (
    build_return_report,
    compute_wilder_atr,
    probability_of_backtest_overfitting,
    summarize_returns,
)


class EvalStatisticsTests(unittest.TestCase):
    def test_atr_normalized_return_path_uses_prior_bar_risk(self):
        candles = [
            stat_candle(0, open_price=100, high=105, low=95, close=100),
            stat_candle(1, open_price=100, high=110, low=100, close=110),
            stat_candle(2, open_price=110, high=120, low=110, close=120),
        ]
        trades = [
            {
                "direction": "long",
                "entry_index": 1,
                "entry_price": 100,
                "exit_index": 2,
                "exit_price": 120,
                "pnl_points": 20,
            }
        ]

        atr = compute_wilder_atr(candles, period=1)
        report = build_return_report(
            candles,
            trades,
            start_index=0,
            tf="1h",
            atr_period=1,
            trial_count=4,
        )

        self.assertEqual([10.0, 10.0, 10.0], atr)
        self.assertEqual(1.0, report["series"][1]["atr_normalized_return"])
        self.assertEqual(1.0, report["series"][2]["atr_normalized_return"])
        self.assertAlmostEqual(0.1, report["series"][1]["simple_return"])
        self.assertAlmostEqual(0.2, report["summary"]["simple"]["total_return"])
        self.assertEqual(2.0, report["summary"]["atr_normalized"]["total_return"])
        self.assertEqual("additive", report["summary"]["atr_normalized"]["path_type"])

    def test_dsr_penalizes_larger_honest_trial_count(self):
        returns = [0.02, -0.005, 0.018, 0.004, 0.015, -0.002, 0.013, 0.006, 0.02, -0.004]

        single_trial = summarize_returns(returns, periods_per_year=252, trial_count=1)
        many_trials = summarize_returns(returns, periods_per_year=252, trial_count=30)

        self.assertGreater(single_trial["annualized_sharpe"], 0)
        self.assertGreater(single_trial["probabilistic_sharpe_sr0"], 0.5)
        self.assertEqual(30, many_trials["dsr_trial_count"])
        self.assertLess(many_trials["deflated_sharpe_ratio"], single_trial["deflated_sharpe_ratio"])
        self.assertGreater(many_trials["dsr_benchmark_sharpe"], 0)

    def test_pbo_cscv_flags_in_sample_winner_that_ranks_poorly_oos(self):
        result = probability_of_backtest_overfitting(
            [
                {
                    "id": "overfit_shape",
                    "returns": [0.10, 0.09, 0.08, 0.07, -0.10, -0.09, -0.08, -0.07],
                },
                {
                    "id": "steady",
                    "returns": [0.01, 0.011, 0.009, 0.010, 0.01, 0.011, 0.009, 0.010],
                },
                {
                    "id": "weak",
                    "returns": [-0.01, -0.011, -0.009, -0.010, -0.01, -0.011, -0.009, -0.010],
                },
            ],
            groups=4,
            metric="mean",
        )

        self.assertEqual(6, result["split_count"])
        self.assertGreater(result["pbo"], 0)
        self.assertTrue(any(row["overfit"] for row in result["logits"]))


def stat_candle(
    index: int,
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> dict[str, float | int]:
    return {
        "ts_ms": index * 3_600_000,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


if __name__ == "__main__":
    unittest.main()
