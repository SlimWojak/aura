from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import TestCase
from unittest.mock import patch

from runtime.market.ingest import pull_ohlcv
from runtime.market.ohlcv import read_candles
from runtime.tools.market_ingest import main as market_main


def charts_payload(*candles):
    return {"candles": list(candles)}


def candle(ts_ms, close="101"):
    return {
        "time": ts_ms,
        "open": "100",
        "high": "102",
        "low": "99",
        "close": close,
        "volume": "1.25",
    }


class FakeHTTPResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


class MarketOHLCVTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.aura_root = Path(self.tempdir.name)

    def test_pull_merges_without_duplicate_timestamps(self):
        with patch("runtime.market.ingest.urlopen") as urlopen:
            urlopen.side_effect = [
                FakeHTTPResponse(charts_payload(candle(1_000), candle(2_000, close="102"))),
                FakeHTTPResponse(charts_payload(candle(2_000, close="202"), candle(3_000))),
            ]

            first = pull_ohlcv(symbol="PF_XBTUSD", tf="1h", aura_root=self.aura_root)
            second = pull_ohlcv(symbol="PF_XBTUSD", tf="1h", aura_root=self.aura_root)

        candles = read_candles("PF_XBTUSD", "1h", aura_root_override=self.aura_root)
        self.assertEqual([1_000, 2_000, 3_000], [row["ts_ms"] for row in candles])
        self.assertEqual("202", candles[1]["close"])
        self.assertEqual(2, first["fetched_count"])
        self.assertEqual(2, second["fetched_count"])
        self.assertEqual(3, second["stored_count"])
        self.assertIn("from=2", urlopen.call_args_list[1].args[0].full_url)

    def test_cli_status_and_show_work(self):
        with patch("runtime.market.ingest.urlopen") as urlopen:
            urlopen.return_value = FakeHTTPResponse(charts_payload(candle(1_000), candle(2_000)))
            pull_output = run_cli(
                [
                    "pull",
                    "--aura-root",
                    str(self.aura_root),
                    "--symbol",
                    "PF_XBTUSD",
                    "--tf",
                    "1h",
                ]
            )

        self.assertTrue(pull_output["ok"])
        status_output = run_cli(["status", "--aura-root", str(self.aura_root)])
        self.assertTrue(status_output["ok"])
        self.assertEqual(1, len(status_output["entries"]))
        self.assertEqual(2, status_output["entries"][0]["candle_count"])
        self.assertEqual(2_000, status_output["entries"][0]["latest_ts_ms"])

        show_output = run_cli(
            [
                "show",
                "--aura-root",
                str(self.aura_root),
                "--symbol",
                "PF_XBTUSD",
                "--tf",
                "1h",
                "--tail",
                "1",
            ]
        )
        self.assertTrue(show_output["ok"])
        self.assertEqual([2_000], [row["ts_ms"] for row in show_output["candles"]])

    def test_pull_uses_charts_http_without_kraken_subprocess(self):
        seen_urls = []

        def fake_urlopen(request, timeout):
            seen_urls.append(request.full_url)
            self.assertEqual(20, timeout)
            return FakeHTTPResponse(charts_payload(candle(1_000)))

        with patch("runtime.market.ingest.urlopen", side_effect=fake_urlopen), patch(
            "subprocess.run",
            wraps=subprocess.run,
        ) as subprocess_run:
            pull_ohlcv(symbol="PF_XBTUSD", tf="1h", aura_root=self.aura_root)

        self.assertEqual(0, subprocess_run.call_count)
        self.assertEqual(1, len(seen_urls))
        self.assertTrue(
            seen_urls[0].startswith(
                "https://futures.kraken.com/api/charts/v1/trade/PF_XBTUSD/1h?"
            )
        )
        self.assertNotIn("funding", seen_urls[0])
        self.assertNotIn("--allow-dangerous", seen_urls[0])
        self.assertNotIn("/all", seen_urls[0])


def run_cli(argv):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = market_main(argv)
    if code != 0:
        raise AssertionError(f"market_ingest exited {code}: {stdout.getvalue()}")
    return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
