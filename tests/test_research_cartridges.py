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
                "ichi_cloud_thickness_v0",
                "ichi_kijun_bounce_trend_v0",
                "ichi_er_regime_v0",
                "ichi_params_20_60_v0",
                "ichi_params_20_60_er_v0",
                "ichi_tk_cloud_strong_v0",
                "ichi_tk_strong_trend_only_v0",
                "ichi_tk_cloud_v0",
                "ichi_v0_baseline",
            },
            {cartridge["id"] for cartridge in cartridges},
        )
        for cartridge in cartridges:
            with self.subTest(cartridge=cartridge["id"]):
                self.assertIn(cartridge["status"], {"draft", "queued", "killed"})
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
        self.assertEqual("killed", cartridge["status"])
        self.assertTrue(any(source.startswith("https://") for source in cartridge["sources"]))

    def test_strict_chikou_seed_uses_open_space_mode(self):
        cartridge = load_cartridge(CARTRIDGE_ROOT / "ichi_chikou_open_space_v0.yaml")

        self.assertEqual("strict", cartridge["entry_rules"]["chikou_mode"])
        self.assertEqual("always_on", cartridge["entry_rules"]["mode"])
        self.assertEqual(
            "tenkan_over_kijun_for_long_under_for_short",
            cartridge["entry_rules"]["require_tk_state"],
        )
        self.assertEqual("killed", cartridge["status"])

    def test_round_two_cartridges_load_requested_modes(self):
        er = load_cartridge(CARTRIDGE_ROOT / "ichi_er_regime_v0.yaml")
        cloud = load_cartridge(CARTRIDGE_ROOT / "ichi_cloud_thickness_v0.yaml")
        slow_er = load_cartridge(CARTRIDGE_ROOT / "ichi_params_20_60_er_v0.yaml")
        tk_strong = load_cartridge(CARTRIDGE_ROOT / "ichi_tk_cloud_strong_v0.yaml")
        trend_only = load_cartridge(CARTRIDGE_ROOT / "ichi_tk_strong_trend_only_v0.yaml")
        kijun_bounce = load_cartridge(CARTRIDGE_ROOT / "ichi_kijun_bounce_trend_v0.yaml")

        self.assertEqual("er", er["regime"]["type"])
        self.assertEqual(10, er["regime"]["params"]["period"])
        self.assertEqual(0.3, er["regime"]["params"]["threshold"])
        self.assertEqual("cloud_thickness", cloud["regime"]["type"])
        self.assertEqual(0.5, cloud["regime"]["params"]["min_pct"])
        self.assertEqual(20, slow_er["ichimoku"]["tenkan"])
        self.assertEqual(50000, slow_er["kill_criteria"]["max_dd_points"])
        self.assertEqual("tk_cloud_bias", tk_strong["entry_rules"]["mode"])
        self.assertEqual("tk_cross_only", tk_strong["entry_rules"]["require_tk_state"])
        self.assertFalse(tk_strong["entry_rules"]["require_chikou_confirmation"])
        self.assertEqual("total_pnl_points_after_fees", trend_only["kill_criteria"]["baseline_metric"])
        self.assertEqual("kijun_bounce", kijun_bounce["entry_rules"]["mode"])
        self.assertEqual("none", kijun_bounce["entry_rules"]["require_tk_state"])

    def test_validate_rejects_unknown_status(self):
        valid = load_cartridge(CARTRIDGE_ROOT / "ichi_v0_baseline.yaml")
        invalid = dict(valid)
        invalid["status"] = "live"

        with self.assertRaisesRegex(ValueError, "status"):
            validate_cartridge(invalid)


if __name__ == "__main__":
    unittest.main()
