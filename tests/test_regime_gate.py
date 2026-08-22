from __future__ import annotations

import unittest
from unittest import TestCase

from runtime.regime import RegimeState, regime_allows


class RegimeGateTests(TestCase):
    def test_gate_matrix_for_all_states_and_entry_sides(self):
        expected = {
            (RegimeState.TREND_BULL, "long"): True,
            (RegimeState.TREND_BULL, "short"): False,
            (RegimeState.TREND_BEAR, "long"): False,
            (RegimeState.TREND_BEAR, "short"): True,
            (RegimeState.RANGE, "long"): False,
            (RegimeState.RANGE, "short"): False,
            (RegimeState.VOLATILE, "long"): False,
            (RegimeState.VOLATILE, "short"): False,
            (RegimeState.TRANSITION, "long"): False,
            (RegimeState.TRANSITION, "short"): False,
        }

        for state in RegimeState:
            for side in ("long", "short"):
                with self.subTest(state=state, side=side):
                    allowed, reasons = regime_allows(side, state)
                    self.assertEqual(expected[(state, side)], allowed)
                    if allowed:
                        self.assertIn("regime_allows", reasons)
                    else:
                        self.assertIn("regime_veto", reasons)

    def test_gate_fails_closed_for_missing_or_unknown_state(self):
        for state in (None, "", "BOGUS"):
            with self.subTest(state=state):
                allowed, reasons = regime_allows("long", state)
                self.assertFalse(allowed)
                self.assertIn("regime_veto", reasons)


if __name__ == "__main__":
    unittest.main()
