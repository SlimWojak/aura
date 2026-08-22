from __future__ import annotations

from datetime import UTC, datetime
import unittest

from runtime.risk import admit


NOW = datetime(2026, 8, 22, 4, 33, tzinfo=UTC)


def proposal(**overrides):
    values = {
        "symbol": "PF_XBTUSD",
        "side": "buy",
        "size": 0.01,
        "order_type": "limit",
        "notional_usd": 450,
        "leverage": 1,
        "client_order_id": "test-order-1",
    }
    values.update(overrides)
    return values


def account_state(**overrides):
    values = {
        "equity": 10_000,
        "open_positions_count": 0,
        "daily_pnl": 0,
        "weekly_pnl": 0,
        "kill_state": "armed",
        "as_of": NOW.isoformat().replace("+00:00", "Z"),
    }
    values.update(overrides)
    return values


class AdmitTests(unittest.TestCase):
    def test_allows_happy_path(self):
        result = admit(proposal(), account_state(), now=NOW)

        self.assertTrue(result.allowed)
        self.assertEqual((), result.reasons)
        self.assertEqual("allow", result.result)

    def test_rejects_oversize_notional(self):
        result = admit(proposal(notional_usd=501), account_state(), now=NOW)

        self.assertFalse(result.allowed)
        self.assertIn("proposal notional_usd exceeds max_notional_usd", result.reasons)

    def test_rejects_max_positions(self):
        result = admit(proposal(), account_state(open_positions_count=2), now=NOW)

        self.assertFalse(result.allowed)
        self.assertIn(
            "account_state open_positions_count at or above max_open_positions",
            result.reasons,
        )

    def test_rejects_soft_kill(self):
        result = admit(proposal(), account_state(kill_state="soft"), now=NOW)

        self.assertFalse(result.allowed)
        self.assertIn("kill_state soft", result.reasons)

    def test_rejects_excess_leverage(self):
        result = admit(proposal(leverage=3), account_state(), now=NOW)

        self.assertFalse(result.allowed)
        self.assertIn("proposal leverage exceeds max_leverage", result.reasons)


if __name__ == "__main__":
    unittest.main()

