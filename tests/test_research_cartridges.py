from __future__ import annotations

from pathlib import Path
import unittest
from unittest import TestCase

from runtime.research.cartridge import load_cartridge, load_cartridges, validate_cartridge


CARTRIDGE_ROOT = Path(__file__).resolve().parents[1] / "research" / "cartridges"


class ResearchCartridgeTests(TestCase):
    def test_seed_cartridges_load_and_validate_required_defaults(self):
        cartridges = load_cartridges(CARTRIDGE_ROOT)

        self.assertEqual(
            {
                "ichi_adx_regime_v0",
                "ichi_chikou_open_space_v0",
                "ichi_params_20_60_v0",
                "ichi_tk_cloud_v0",
                "ichi_v0_baseline",
            },
            {cartridge["id"] for cartridge in cartridges},
        )
        for cartridge in cartridges:
            with self.subTest(cartridge=cartridge["id"]):
                self.assertIn(cartridge["status"], {"draft", "queued"})
                self.assertEqual("PF_XBTUSD", cartridge["symbol"])
                self.assertEqual("1h", cartridge["tf"])
                self.assertEqual("ichimoku_v0", cartridge["baseline_ref"])
                self.assertEqual({"long", "short"}, set(cartridge["entry_rules"]["allowed_sides"]))
                self.assertIn(cartridge["entry_rules"]["chikou_mode"], {"close", "strict"})
                self.assertGreater(cartridge["kill_criteria"]["max_dd_points"], 0)

    def test_load_single_seed_with_url_source(self):
        cartridge = load_cartridge(CARTRIDGE_ROOT / "ichi_adx_regime_v0.yaml")

        self.assertEqual("adx", cartridge["regime"]["type"])
        self.assertEqual(25, cartridge["regime"]["params"]["threshold"])
        self.assertTrue(any(source.startswith("https://") for source in cartridge["sources"]))

    def test_strict_chikou_seed_uses_open_space_mode(self):
        cartridge = load_cartridge(CARTRIDGE_ROOT / "ichi_chikou_open_space_v0.yaml")

        self.assertEqual("strict", cartridge["entry_rules"]["chikou_mode"])
        self.assertEqual("always_on", cartridge["entry_rules"]["mode"])
        self.assertEqual(
            "tenkan_over_kijun_for_long_under_for_short",
            cartridge["entry_rules"]["require_tk_state"],
        )

    def test_validate_rejects_unknown_status(self):
        valid = load_cartridge(CARTRIDGE_ROOT / "ichi_v0_baseline.yaml")
        invalid = dict(valid)
        invalid["status"] = "live"

        with self.assertRaisesRegex(ValueError, "status"):
            validate_cartridge(invalid)


if __name__ == "__main__":
    unittest.main()
