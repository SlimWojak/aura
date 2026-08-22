from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import TestCase

from runtime.brain import compute_ichimoku, signal_from_series
from runtime.market.ohlcv import SOURCE, ohlcv_path, write_candles
from runtime.tools.ichimoku_signal import main as ichimoku_main


class IchimokuSignalTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_hand_checked_tenkan_and_kijun_on_short_series(self):
        candles = [
            candle(index, high=index + 10, low=index, close=index + 5)
            for index in range(26)
        ]

        series = compute_ichimoku(candles)

        self.assertFalse(series.ok)
        self.assertIn("insufficient_history", series.reason)
        latest = series.points[-1]
        self.assertEqual(26.0, latest.tenkan)
        self.assertEqual(17.5, latest.kijun)
        self.assertIsNone(latest.senkou_span_b_raw)

    def test_insufficient_history_returns_error_signal(self):
        series = compute_ichimoku([candle(index, close=100) for index in range(20)])
        signal = signal_from_series(series)

        self.assertFalse(series.ok)
        self.assertFalse(signal.ok)
        self.assertEqual("flat", signal.bias)
        self.assertIn("insufficient_history", signal.reason)

    def test_flat_signal_from_constant_series(self):
        signal = signal_from_series(
            compute_ichimoku([candle(index, high=101, low=99, close=100) for index in range(90)])
        )

        self.assertTrue(signal.ok)
        self.assertEqual("flat", signal.bias)
        self.assertFalse(signal.features["bullish_rule"])
        self.assertFalse(signal.features["bearish_rule"])

    def test_long_signal_from_rising_synthetic_series(self):
        signal = signal_from_series(compute_ichimoku(trending_candles(direction=1)))

        self.assertTrue(signal.ok)
        self.assertEqual("long", signal.bias)
        self.assertTrue(signal.features["close_above_cloud"])
        self.assertTrue(signal.features["tenkan_above_kijun"])
        self.assertTrue(signal.features["chikou_above_reference"])

    def test_short_signal_from_falling_synthetic_series(self):
        signal = signal_from_series(compute_ichimoku(trending_candles(direction=-1)))

        self.assertTrue(signal.ok)
        self.assertEqual("short", signal.bias)
        self.assertTrue(signal.features["close_below_cloud"])
        self.assertTrue(signal.features["tenkan_below_kijun"])
        self.assertTrue(signal.features["chikou_below_reference"])

    def test_strict_chikou_requires_close_to_clear_reference_high(self):
        candles = trending_candles(direction=1)
        candles[63] = candle(63, high=126, low=99, close=100)
        series = compute_ichimoku(candles)

        baseline = signal_from_series(series, chikou_mode="close")
        strict = signal_from_series(series, chikou_mode="strict")

        self.assertEqual("long", baseline.bias)
        self.assertEqual("flat", strict.bias)
        self.assertTrue(baseline.features["chikou_above_reference"])
        self.assertFalse(strict.features["chikou_above_reference"])
        self.assertEqual(126.0, strict.components["chikou_reference_high"])

    def test_cli_compute_reads_temp_aura_root_jsonl(self):
        write_market_candles(self.aura_root, trending_candles(direction=1))

        output = run_cli(
            [
                "compute",
                "--aura-root",
                str(self.aura_root),
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
            ]
        )

        self.assertTrue(output["ok"])
        self.assertEqual("long", output["bias"])
        self.assertEqual("PF_XBTUSD", output["symbol"])
        self.assertEqual("1h", output["tf"])
        self.assertEqual(90, output["candle_count"])

    def test_cli_evaluate_writes_brain_signal_jsonl(self):
        write_market_candles(self.aura_root, trending_candles(direction=1))

        output = run_cli(
            [
                "evaluate",
                "--aura-root",
                str(self.aura_root),
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
                "--trial-id",
                "T-ichi-test",
            ]
        )

        self.assertTrue(output["ok"])
        path = self.aura_root / "evidence" / "trials" / "T-ichi-test" / "decision.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, len(lines))
        event = json.loads(lines[0])
        self.assertEqual("aura.brain_signal.v1", event["schema"])
        self.assertEqual("brain_signal", event["intent"])
        self.assertEqual("long", event["signal"]["bias"])
        self.assertFalse(event["paper"]["requested"])


def trending_candles(*, direction: int) -> list[dict[str, str | int]]:
    candles = []
    for index in range(90):
        if index < 65:
            close = 100
        else:
            close = 100 + (direction * (index - 64))
        candles.append(candle(index, high=close + 1, low=close - 1, close=close))
    return candles


def candle(
    index: int,
    *,
    high: int | float | None = None,
    low: int | float | None = None,
    close: int | float = 100,
) -> dict[str, str | int]:
    resolved_high = close + 1 if high is None else high
    resolved_low = close - 1 if low is None else low
    return {
        "schema": "aura.ohlcv_candle.v1",
        "symbol": "PF_XBTUSD",
        "tf": "1h",
        "ts_ms": index * 3_600_000,
        "source": SOURCE,
        "ingested_at": "2026-08-22T00:00:00Z",
        "open": str(close),
        "high": str(resolved_high),
        "low": str(resolved_low),
        "close": str(close),
        "volume": "1",
    }


def write_market_candles(aura_root: Path, candles: list[dict[str, str | int]]) -> None:
    write_candles(
        ohlcv_path("PF_XBTUSD", "1h", aura_root_override=aura_root),
        candles,
    )


def run_cli(argv):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = ichimoku_main(argv)
    if code != 0:
        raise AssertionError(f"ichimoku_signal exited {code}: {stdout.getvalue()}")
    return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
