from __future__ import annotations

from unittest import TestCase

from runtime.eval.ic_screen import build_bar_feature_rows
from runtime.market.ohlcv import CANDLE_SCHEMA, SOURCE
from runtime.regime.enrichment import (
    FairValueGap,
    daily_dealing_range_series,
    dealing_range_position,
    dealing_range_side,
    flat_spanb_overlaps_fvg,
    latest_fvg_series,
)
from runtime.regime.types import RegimeParams


FAST_PARAMS = RegimeParams(
    tenkan=2,
    kijun=3,
    senkou_b=4,
    displacement=2,
    adx_period=3,
    flat_n=2,
    use_htf_veto=False,
    use_kumo_width_atr=False,
)


class EnrichmentFeatureTests(TestCase):
    def test_classic_three_candle_fvg_detection(self):
        candles = [
            daily_candle(0, high=100, low=90, close=95),
            daily_candle(1, high=105, low=95, close=100),
            daily_candle(2, high=120, low=110, close=115),
            daily_candle(3, high=90, low=80, close=85),
        ]

        gaps = latest_fvg_series(candles, tf="1d")

        self.assertIsNone(gaps[0])
        self.assertIsNone(gaps[1])
        self.assertIsNotNone(gaps[2])
        self.assertEqual("bullish", gaps[2].side)
        self.assertEqual(100, gaps[2].lower)
        self.assertEqual(110, gaps[2].upper)
        self.assertIsNotNone(gaps[3])
        self.assertEqual("bearish", gaps[3].side)
        self.assertEqual(90, gaps[3].lower)
        self.assertEqual(95, gaps[3].upper)

    def test_daily_dealing_range_side_uses_confirmed_swings(self):
        candles = [
            daily_candle(0, high=10, low=7, close=8),
            daily_candle(1, high=12, low=8, close=10),
            daily_candle(2, high=20, low=9, close=18),
            daily_candle(3, high=14, low=5, close=7),
            daily_candle(4, high=13, low=7, close=11),
        ]

        ranges = daily_dealing_range_series(candles)

        self.assertIsNone(ranges[3])
        dealing_range = ranges[4]
        self.assertIsNotNone(dealing_range)
        self.assertEqual(5, dealing_range.low)
        self.assertEqual(20, dealing_range.high)
        self.assertEqual("discount", dealing_range_side(10, dealing_range))
        self.assertEqual("equilibrium", dealing_range_side(12.5, dealing_range))
        self.assertEqual("premium", dealing_range_side(15, dealing_range))
        self.assertAlmostEqual(-1.0, dealing_range_position(5, dealing_range))
        self.assertAlmostEqual(1.0, dealing_range_position(20, dealing_range))

    def test_chikou_daily_dr_alignment_ignores_future_daily_mutation(self):
        candles = hourly_from_daily(
            [
                (110, 100, 105),
                (120, 104, 112),
                (150, 108, 130),
                (130, 90, 100),
                (125, 95, 110),
                (165, 100, 160),
                (170, 120, 150),
            ]
        )
        target_index = (5 * 24) + 6

        baseline = build_bar_feature_rows(
            candles,
            tf="1h",
            params=FAST_PARAMS,
            atr_period=3,
            symbol="PF_XBTUSD",
            feature_set="enrichment",
        )

        mutated = list(candles)
        for index in range(6 * 24, 7 * 24):
            changed = dict(mutated[index])
            changed["high"] = "10000"
            changed["low"] = "9990"
            changed["close"] = "9995"
            mutated[index] = changed
        treatment = build_bar_feature_rows(
            mutated,
            tf="1h",
            params=FAST_PARAMS,
            atr_period=3,
            symbol="PF_XBTUSD",
            feature_set="enrichment",
        )

        self.assertTrue(baseline[target_index]["chikou_clears_daily_dr"])
        self.assertEqual(
            baseline[target_index]["chikou_clears_daily_dr"],
            treatment[target_index]["chikou_clears_daily_dr"],
        )
        self.assertEqual(
            baseline[target_index]["chikou_daily_dr_clearance_atr"],
            treatment[target_index]["chikou_daily_dr_clearance_atr"],
        )

    def test_flat_spanb_overlap_requires_flat_spanb_inside_gap(self):
        gap = FairValueGap(tf="1d", side="bullish", lower=100, upper=110, detected_ts_ms=0)

        self.assertTrue(
            flat_spanb_overlaps_fvg(span_b=105, flat_spanb_bars=4, flat_n=3, gap=gap)
        )
        self.assertFalse(
            flat_spanb_overlaps_fvg(span_b=105, flat_spanb_bars=2, flat_n=3, gap=gap)
        )
        self.assertFalse(
            flat_spanb_overlaps_fvg(span_b=115, flat_spanb_bars=4, flat_n=3, gap=gap)
        )


def daily_candle(day: int, *, high: int | float, low: int | float, close: int | float) -> dict[str, str | int]:
    return {
        "schema": CANDLE_SCHEMA,
        "symbol": "PF_XBTUSD",
        "tf": "1d",
        "ts_ms": day * 24 * 3_600_000,
        "source": SOURCE,
        "ingested_at": "2026-08-22T00:00:00Z",
        "open": str(close),
        "high": str(high),
        "low": str(low),
        "close": str(close),
        "volume": "24",
    }


def hourly_from_daily(daily_values: list[tuple[int | float, int | float, int | float]]) -> list[dict[str, str | int]]:
    candles = []
    for day, (high, low, close) in enumerate(daily_values):
        for hour in range(24):
            index = (day * 24) + hour
            candles.append(
                {
                    "schema": CANDLE_SCHEMA,
                    "symbol": "PF_XBTUSD",
                    "tf": "1h",
                    "ts_ms": index * 3_600_000,
                    "source": SOURCE,
                    "ingested_at": "2026-08-22T00:00:00Z",
                    "open": str(close),
                    "high": str(high),
                    "low": str(low),
                    "close": str(close),
                    "volume": "1",
                }
            )
    return candles
