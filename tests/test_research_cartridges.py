from __future__ import annotations

from pathlib import Path
import unittest
from unittest import TestCase

from runtime.research.cartridge import (
    STATUS_VALUES,
    load_cartridge,
    load_cartridges,
    validate_cartridge,
)


CARTRIDGE_ROOT = Path(__file__).resolve().parents[1] / "research" / "cartridges"


class ResearchCartridgeTests(TestCase):
    def test_seed_cartridges_load_and_validate_required_defaults(self):
        cartridges = load_cartridges(CARTRIDGE_ROOT)

        self.assertEqual(
            {
                "ichi_adx_regime_v0",
                "ichi_always_on_tsmom_thin_v0",
                "ichi_chikou_open_space_v0",
                "ichi_cloud_thickness_v0",
                "ichi_cloud_bias_tsmom_4h_v0",
                "ichi_cloud_bias_tsmom_thin_v0",
                "ichi_kijun_bounce_trend_v0",
                "ichi_er_regime_v0",
                "ichi_kumo_break_thin_v0",
                "ichi_kumo_break_trend_v0",
                "ichi_p2_ab0_eth_v0",
                "ichi_p2_ab0_xbt_v0",
                "ichi_p2_abfull_eth_v0",
                "ichi_p2_abfull_xbt_v0",
                "ichi_p2_abnoadx_eth_v0",
                "ichi_p2_abnoadx_xbt_v0",
                "ichi_p2_abnodwell_eth_v0",
                "ichi_p2_abnodwell_xbt_v0",
                "ichi_p2_abnohtf_eth_v0",
                "ichi_p2_abnohtf_xbt_v0",
                "ichi_p2_abnowidth_eth_v0",
                "ichi_p2_abnowidth_xbt_v0",
                "ichi_params_10_30_trend_v0",
                "ichi_params_20_60_v0",
                "ichi_params_20_60_er_v0",
                "ichi_params_20_60_trend_v0",
                "ichi_params_20_60_trend_btc_confirm_eth_v0",
                "ichi_params_20_60_trend_eth_dd_v0",
                "ichi_params_20_60_trend_long_only_v0",
                "ichi_params_20_60_trend_long_only_n8_v0",
                "ichi_params_20_60_trend_regime_exit_v0",
                "ichi_params_20_60_trend_timestop_v0",
                "ichi_tenkan_bounce_trend_v0",
                "ichi_tk_cloud_strong_v0",
                "ichi_tk_strong_trend_cloud_color_v0",
                "ichi_tk_strong_trend_kijun_dip_v0",
                "ichi_tk_strong_trend_oos_v0",
                "ichi_tk_strong_trend_only_v0",
                "ichi_tk_cloud_v0",
                "ichi_tk_cross_trend_v0",
                "ichi_v0_trend_eth_primary_v0",
                "ichi_v0_trend_atr_stop_v0",
                "ichi_v0_trend_chandelier_v0",
                "ichi_v0_trend_kijun_trail_v0",
                "ichi_v0_baseline",
            },
            {cartridge["id"] for cartridge in cartridges},
        )
        for cartridge in cartridges:
            with self.subTest(cartridge=cartridge["id"]):
                self.assertIn(cartridge["status"], STATUS_VALUES)
                if cartridge["id"] in {
                    "ichi_params_20_60_trend_btc_confirm_eth_v0",
                    "ichi_v0_trend_eth_primary_v0",
                    "ichi_p2_ab0_eth_v0",
                    "ichi_p2_abfull_eth_v0",
                    "ichi_p2_abnoadx_eth_v0",
                    "ichi_p2_abnodwell_eth_v0",
                    "ichi_p2_abnohtf_eth_v0",
                    "ichi_p2_abnowidth_eth_v0",
                }:
                    self.assertEqual("PF_ETHUSD", cartridge["symbol"])
                else:
                    self.assertEqual("PF_XBTUSD", cartridge["symbol"])
                if cartridge["id"] == "ichi_cloud_bias_tsmom_4h_v0":
                    self.assertEqual("4h", cartridge["tf"])
                else:
                    self.assertEqual("1h", cartridge["tf"])
                self.assertIn(
                    cartridge["baseline_ref"],
                    {
                        "ichimoku_v0",
                        "ichi_tk_strong_trend_only_v0",
                        "ichi_v0_baseline",
                        "ichi_params_20_60_trend_v0",
                        "ichi_p2_abfull_eth_v0",
                        "ichi_p2_abfull_xbt_v0",
                    },
                )
                allowed_sides = set(cartridge["entry_rules"]["allowed_sides"])
                if cartridge["id"] in {
                    "ichi_params_20_60_trend_long_only_v0",
                    "ichi_params_20_60_trend_long_only_n8_v0",
                }:
                    self.assertEqual({"long"}, allowed_sides)
                else:
                    self.assertEqual({"long", "short"}, allowed_sides)
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
        trend_oos = load_cartridge(CARTRIDGE_ROOT / "ichi_tk_strong_trend_oos_v0.yaml")
        kijun_dip = load_cartridge(CARTRIDGE_ROOT / "ichi_tk_strong_trend_kijun_dip_v0.yaml")
        cloud_color = load_cartridge(CARTRIDGE_ROOT / "ichi_tk_strong_trend_cloud_color_v0.yaml")
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
        self.assertEqual("killed", trend_only["status"])
        self.assertIn("OOS failed", trend_only["notes"])
        self.assertIn("docs/LEDGER.md", trend_only["sources"])
        self.assertIn("70/30", trend_oos["kill_criteria"]["notes"])
        self.assertEqual("total_pnl_points_after_fees", trend_oos["kill_criteria"]["baseline_metric"])
        self.assertTrue(kijun_dip["entry_rules"]["require_kijun_dip_setup"])
        self.assertEqual(8, kijun_dip["entry_rules"]["setup_bars"])
        self.assertEqual("ichi_tk_strong_trend_only_v0", kijun_dip["baseline_ref"])
        self.assertTrue(cloud_color["entry_rules"]["require_cloud_color_align"])
        self.assertEqual("ichi_tk_strong_trend_only_v0", cloud_color["baseline_ref"])
        self.assertEqual("kijun_bounce", kijun_bounce["entry_rules"]["mode"])
        self.assertEqual("none", kijun_bounce["entry_rules"]["require_tk_state"])
        self.assertEqual("killed", kijun_bounce["status"])
        self.assertIn("docs/LEDGER.md", kijun_bounce["sources"])

    def test_round_three_entry_family_cartridges_load_requested_modes(self):
        slow_trend = load_cartridge(CARTRIDGE_ROOT / "ichi_params_20_60_trend_v0.yaml")
        tk_cross = load_cartridge(CARTRIDGE_ROOT / "ichi_tk_cross_trend_v0.yaml")
        kumo_break = load_cartridge(CARTRIDGE_ROOT / "ichi_kumo_break_trend_v0.yaml")

        self.assertEqual("ichi_v0_baseline", slow_trend["baseline_ref"])
        self.assertEqual(20, slow_trend["ichimoku"]["tenkan"])
        self.assertEqual(60, slow_trend["ichimoku"]["kijun"])
        self.assertEqual("always_on", slow_trend["entry_rules"]["mode"])
        self.assertTrue(slow_trend["entry_rules"]["require_chikou_confirmation"])
        self.assertEqual("total_pnl_points_after_fees", slow_trend["kill_criteria"]["baseline_metric"])
        self.assertIn("70/30", slow_trend["notes"])
        self.assertEqual("scarred_control", slow_trend["status"])
        self.assertIn("docs/LEDGER.md", slow_trend["sources"])
        self.assertIn("Track A/R7 honesty", slow_trend["notes"])
        self.assertIn("ETH secondary OOS", slow_trend["kill_criteria"]["notes"])

        self.assertEqual("ichi_v0_baseline", tk_cross["baseline_ref"])
        self.assertEqual("tk_cross", tk_cross["entry_rules"]["mode"])
        self.assertEqual("tk_cross_only", tk_cross["entry_rules"]["require_tk_state"])
        self.assertFalse(tk_cross["entry_rules"]["require_chikou_confirmation"])
        self.assertIn("not both-lines-outside TK-strong", tk_cross["notes"])
        self.assertEqual("killed", tk_cross["status"])
        self.assertIn("docs/LEDGER.md", tk_cross["sources"])
        self.assertIn("PF_XBTUSD OOS pass_oos_gate=false", tk_cross["kill_criteria"]["notes"])

        self.assertEqual("ichi_v0_baseline", kumo_break["baseline_ref"])
        self.assertEqual("kumo_break", kumo_break["entry_rules"]["mode"])
        self.assertEqual("none", kumo_break["entry_rules"]["require_tk_state"])
        self.assertFalse(kumo_break["entry_rules"]["require_chikou_confirmation"])
        self.assertIn("current close breaks above", kumo_break["notes"])
        self.assertEqual("killed", kumo_break["status"])
        self.assertIn("docs/LEDGER.md", kumo_break["sources"])
        self.assertIn("fee-negative OOS", kumo_break["kill_criteria"]["notes"])

    def test_round_four_research_intern_cartridges_load_requested_modes(self):
        slow_eth_dd = load_cartridge(
            CARTRIDGE_ROOT / "ichi_params_20_60_trend_eth_dd_v0.yaml"
        )
        mid_pack = load_cartridge(CARTRIDGE_ROOT / "ichi_params_10_30_trend_v0.yaml")
        tenkan_bounce = load_cartridge(CARTRIDGE_ROOT / "ichi_tenkan_bounce_trend_v0.yaml")

        self.assertEqual("ichi_v0_baseline", slow_eth_dd["baseline_ref"])
        self.assertEqual(20, slow_eth_dd["ichimoku"]["tenkan"])
        self.assertEqual(60, slow_eth_dd["ichimoku"]["kijun"])
        self.assertEqual(25000, slow_eth_dd["kill_criteria"]["max_dd_points"])
        self.assertEqual("total_pnl_points_after_fees", slow_eth_dd["kill_criteria"]["baseline_metric"])
        self.assertEqual("killed", slow_eth_dd["status"])
        self.assertIn("docs/LEDGER.md", slow_eth_dd["sources"])
        self.assertIn("ETH OOS was required", slow_eth_dd["notes"])
        self.assertIn("new id only", slow_eth_dd["notes"])

        self.assertEqual("ichi_v0_baseline", mid_pack["baseline_ref"])
        self.assertEqual(10, mid_pack["ichimoku"]["tenkan"])
        self.assertEqual(30, mid_pack["ichimoku"]["kijun"])
        self.assertEqual(60, mid_pack["ichimoku"]["senkou_b"])
        self.assertEqual(30, mid_pack["ichimoku"]["displacement"])
        self.assertEqual("always_on", mid_pack["entry_rules"]["mode"])
        self.assertTrue(mid_pack["entry_rules"]["require_chikou_confirmation"])
        self.assertEqual("killed", mid_pack["status"])
        self.assertIn("docs/LEDGER.md", mid_pack["sources"])
        self.assertIn("Mid pack 10/30/60/30", mid_pack["notes"])
        self.assertIn("Does not displace the 20/60 keep", mid_pack["notes"])

        self.assertEqual("ichi_v0_baseline", tenkan_bounce["baseline_ref"])
        self.assertEqual("tenkan_bounce", tenkan_bounce["entry_rules"]["mode"])
        self.assertEqual("none", tenkan_bounce["entry_rules"]["require_tk_state"])
        self.assertFalse(tenkan_bounce["entry_rules"]["require_chikou_confirmation"])
        self.assertEqual("flat_on_rule_fail", tenkan_bounce["exit_rules"]["mode"])
        self.assertEqual(15, tenkan_bounce["kill_criteria"]["min_trades"])
        self.assertEqual("killed", tenkan_bounce["status"])
        self.assertIn("docs/LEDGER.md", tenkan_bounce["sources"])
        self.assertIn("killed kijun_bounce", tenkan_bounce["kill_criteria"]["notes"])
        self.assertIn("fee-on negative", tenkan_bounce["notes"])
        self.assertIn("prior close <= prior Tenkan", tenkan_bounce["notes"])

    def test_round_five_research_intern_cartridges_load_requested_modes(self):
        time_stop = load_cartridge(
            CARTRIDGE_ROOT / "ichi_params_20_60_trend_timestop_v0.yaml"
        )
        long_only = load_cartridge(
            CARTRIDGE_ROOT / "ichi_params_20_60_trend_long_only_v0.yaml"
        )
        regime_exit = load_cartridge(
            CARTRIDGE_ROOT / "ichi_params_20_60_trend_regime_exit_v0.yaml"
        )

        self.assertEqual("ichi_v0_baseline", time_stop["baseline_ref"])
        self.assertEqual(20, time_stop["ichimoku"]["tenkan"])
        self.assertEqual(60, time_stop["ichimoku"]["kijun"])
        self.assertEqual("time_stop", time_stop["exit_rules"]["mode"])
        self.assertEqual(72, time_stop["exit_rules"]["max_bars_in_trade"])
        self.assertEqual(12000, time_stop["kill_criteria"]["max_dd_points"])
        self.assertEqual("killed", time_stop["status"])
        self.assertIn("docs/LEDGER.md", time_stop["sources"])
        self.assertIn("R5 Curator status bank", time_stop["notes"])
        self.assertIn("OOS DD not better than parent", time_stop["notes"])
        self.assertIn("PF_XBTUSD OOS pass_oos_gate=false", time_stop["kill_criteria"]["notes"])

        self.assertEqual(["long"], long_only["entry_rules"]["allowed_sides"])
        self.assertEqual("bias_flip", long_only["exit_rules"]["mode"])
        self.assertIsNone(long_only["exit_rules"]["max_bars_in_trade"])
        self.assertEqual(10, long_only["kill_criteria"]["min_trades"])
        self.assertIn("Long only when TREND_BULL", long_only["notes"])
        self.assertEqual("killed", long_only["status"])
        self.assertIn("docs/LEDGER.md", long_only["sources"])
        self.assertIn("OOS trades 9 < min 10", long_only["notes"])
        self.assertIn("PF_ETHUSD OOS pass_oos_gate=false", long_only["kill_criteria"]["notes"])

        self.assertEqual(["long", "short"], regime_exit["entry_rules"]["allowed_sides"])
        self.assertEqual("regime_exit", regime_exit["exit_rules"]["mode"])
        self.assertIsNone(regime_exit["exit_rules"]["max_bars_in_trade"])
        self.assertEqual(12, regime_exit["kill_criteria"]["min_trades"])
        self.assertIn("long exits when no longer TREND_BULL", regime_exit["notes"])
        self.assertEqual("killed", regime_exit["status"])
        self.assertIn("docs/LEDGER.md", regime_exit["sources"])
        self.assertIn("BTC OOS fee-negative and DD >12000", regime_exit["notes"])
        self.assertIn("PF_XBTUSD OOS pass_oos_gate=false", regime_exit["kill_criteria"]["notes"])

    def test_round_six_research_intern_cartridges_load_requested_modes(self):
        btc_confirm = load_cartridge(
            CARTRIDGE_ROOT / "ichi_params_20_60_trend_btc_confirm_eth_v0.yaml"
        )
        eth_primary = load_cartridge(CARTRIDGE_ROOT / "ichi_v0_trend_eth_primary_v0.yaml")
        long_only_n8 = load_cartridge(
            CARTRIDGE_ROOT / "ichi_params_20_60_trend_long_only_n8_v0.yaml"
        )

        self.assertEqual("PF_ETHUSD", btc_confirm["symbol"])
        self.assertEqual("PF_XBTUSD", btc_confirm["entry_rules"]["confirm_symbol"])
        self.assertTrue(btc_confirm["entry_rules"]["require_confirm_same_bar"])
        self.assertEqual(20, btc_confirm["ichimoku"]["tenkan"])
        self.assertEqual(60, btc_confirm["ichimoku"]["kijun"])
        self.assertEqual(2000, btc_confirm["kill_criteria"]["max_dd_points"])
        self.assertEqual(10, btc_confirm["kill_criteria"]["min_trades"])
        self.assertIn("no-op", btc_confirm["kill_criteria"]["notes"])
        self.assertIn("same-bar PF_XBTUSD", btc_confirm["notes"])
        self.assertEqual("killed", btc_confirm["status"])
        self.assertIn("docs/LEDGER.md", btc_confirm["sources"])
        self.assertIn("must-beat OOS baseline", btc_confirm["kill_criteria"]["notes"])

        self.assertEqual("PF_ETHUSD", eth_primary["symbol"])
        self.assertEqual(9, eth_primary["ichimoku"]["tenkan"])
        self.assertEqual(26, eth_primary["ichimoku"]["kijun"])
        self.assertEqual(500, eth_primary["kill_criteria"]["max_dd_points"])
        self.assertEqual(15, eth_primary["kill_criteria"]["min_trades"])
        self.assertIn("BTC is secondary", eth_primary["kill_criteria"]["notes"])
        self.assertEqual("killed", eth_primary["status"])
        self.assertIn("docs/LEDGER.md", eth_primary["sources"])
        self.assertIn("Identical to fee-on regime-gated ichi_v0_baseline", eth_primary["notes"])

        self.assertEqual("PF_XBTUSD", long_only_n8["symbol"])
        self.assertEqual(["long"], long_only_n8["entry_rules"]["allowed_sides"])
        self.assertEqual(8, long_only_n8["kill_criteria"]["min_trades"])
        self.assertEqual(12000, long_only_n8["kill_criteria"]["max_dd_points"])
        self.assertIn("New id only", long_only_n8["kill_criteria"]["notes"])
        self.assertEqual("killed", long_only_n8["status"])
        self.assertIn("docs/LEDGER.md", long_only_n8["sources"])
        self.assertIn("IS DD >12000", long_only_n8["notes"])

    def test_track_c_exit_vocabulary_kills_load_requested_modes(self):
        kijun_trail = load_cartridge(
            CARTRIDGE_ROOT / "ichi_v0_trend_kijun_trail_v0.yaml"
        )
        chandelier = load_cartridge(
            CARTRIDGE_ROOT / "ichi_v0_trend_chandelier_v0.yaml"
        )
        atr_stop = load_cartridge(CARTRIDGE_ROOT / "ichi_v0_trend_atr_stop_v0.yaml")

        for cartridge in (kijun_trail, chandelier, atr_stop):
            with self.subTest(cartridge=cartridge["id"]):
                self.assertEqual("killed", cartridge["status"])
                self.assertEqual("ichi_params_20_60_trend_v0", cartridge["baseline_ref"])
                self.assertEqual(20, cartridge["ichimoku"]["tenkan"])
                self.assertEqual(60, cartridge["ichimoku"]["kijun"])
                self.assertFalse(cartridge["exit_rules"]["close_on_flat"])
                self.assertFalse(cartridge["exit_rules"]["close_on_opposite"])
                self.assertEqual(
                    "atr_normalized_total_return",
                    cartridge["kill_criteria"]["baseline_metric"],
                )
                self.assertIn("70/30 fee-on OOS", cartridge["kill_criteria"]["notes"])
                self.assertIn("docs/LEDGER.md", cartridge["sources"])
                self.assertIn("Killed forever", cartridge["notes"])
                self.assertIn("new id only", cartridge["notes"])

        self.assertEqual("kijun_trail", kijun_trail["exit_rules"]["mode"])
        self.assertNotIn("kijun_period", kijun_trail["exit_rules"])
        self.assertIn("17.38", kijun_trail["notes"])
        self.assertIn("1.17x parent", kijun_trail["kill_criteria"]["notes"])
        self.assertEqual("chandelier_trail", chandelier["exit_rules"]["mode"])
        self.assertEqual(22, chandelier["exit_rules"]["chandelier_period"])
        self.assertEqual(14, chandelier["exit_rules"]["atr_period"])
        self.assertEqual(3.0, chandelier["exit_rules"]["atr_mult"])
        self.assertIn("deeply negative", chandelier["kill_criteria"]["notes"])
        self.assertEqual("atr_stop", atr_stop["exit_rules"]["mode"])
        self.assertEqual(14, atr_stop["exit_rules"]["atr_period"])
        self.assertEqual(3.0, atr_stop["exit_rules"]["atr_mult"])
        self.assertIn("trades were 4 < 12", atr_stop["kill_criteria"]["notes"])

    def test_round_seven_research_intern_thin_spine_cartridges_load_requested_modes(self):
        kumo_break = load_cartridge(CARTRIDGE_ROOT / "ichi_kumo_break_thin_v0.yaml")
        always_on = load_cartridge(CARTRIDGE_ROOT / "ichi_always_on_tsmom_thin_v0.yaml")
        cloud_bias = load_cartridge(CARTRIDGE_ROOT / "ichi_cloud_bias_tsmom_thin_v0.yaml")
        expected_statuses = {
            "ichi_kumo_break_thin_v0": "killed",
            "ichi_always_on_tsmom_thin_v0": "scarred_control",
            "ichi_cloud_bias_tsmom_thin_v0": "champion_control",
        }

        for cartridge in (kumo_break, always_on, cloud_bias):
            with self.subTest(cartridge=cartridge["id"]):
                self.assertEqual(expected_statuses[cartridge["id"]], cartridge["status"])
                self.assertEqual("PF_XBTUSD", cartridge["symbol"])
                self.assertEqual("ichi_v0_baseline", cartridge["baseline_ref"])
                self.assertEqual(
                    {
                        "tenkan": 9,
                        "kijun": 26,
                        "senkou_b": 52,
                        "displacement": 26,
                    },
                    cartridge["ichimoku"],
                )
                self.assertEqual("bias_flip", cartridge["exit_rules"]["mode"])
                self.assertEqual({"type": "none", "params": {}}, cartridge["regime"])
                self.assertEqual(
                    "atr_normalized_total_return",
                    cartridge["kill_criteria"]["baseline_metric"],
                )
                self.assertIn("--regime-tf 4h --regime-htf 1d", cartridge["notes"])
                self.assertIn("--oos-split 0.7 --atr-period 14", cartridge["notes"])
                self.assertIn("--trial-count 37 --metrics-only", cartridge["notes"])
                self.assertIn("docs/LEDGER.md", cartridge["sources"])
                self.assertIn("R7 thin-spine Intern bank", cartridge["notes"])

        self.assertEqual("kumo_break", kumo_break["entry_rules"]["mode"])
        self.assertEqual("none", kumo_break["entry_rules"]["require_tk_state"])
        self.assertFalse(kumo_break["entry_rules"]["require_chikou_confirmation"])
        self.assertIn("Killed forever", kumo_break["notes"])
        self.assertIn("-15.91", kumo_break["notes"])
        self.assertIn(
            "Never revive ichi_kumo_break_trend_v0",
            kumo_break["kill_criteria"]["notes"],
        )

        self.assertEqual("always_on", always_on["entry_rules"]["mode"])
        self.assertEqual(
            "tenkan_over_kijun_for_long_under_for_short",
            always_on["entry_rules"]["require_tk_state"],
        )
        self.assertFalse(always_on["entry_rules"]["require_chikou_confirmation"])
        self.assertIn("CLI Phase-2 hard veto only", always_on["kill_criteria"]["notes"])
        self.assertIn("not live", always_on["notes"])
        self.assertIn("not a forever-kill", always_on["notes"])
        self.assertIn("64.55", always_on["notes"])
        self.assertIn("34.92", always_on["notes"])

        self.assertEqual("cloud_bias", cloud_bias["entry_rules"]["mode"])
        self.assertEqual("none", cloud_bias["entry_rules"]["require_tk_state"])
        self.assertFalse(cloud_bias["entry_rules"]["require_chikou_confirmation"])
        self.assertIn("not live", cloud_bias["notes"])
        self.assertIn("Best residual R7 ATR control", cloud_bias["notes"])
        self.assertIn("120.35", cloud_bias["notes"])
        self.assertIn("190.88", cloud_bias["notes"])
        self.assertIn("trades 362 versus 338", cloud_bias["kill_criteria"]["notes"])

    def test_one_shot_four_hour_cloud_bias_draft_loads_requested_contract(self):
        cartridge = load_cartridge(CARTRIDGE_ROOT / "ichi_cloud_bias_tsmom_4h_v0.yaml")

        self.assertEqual("draft", cartridge["status"])
        self.assertEqual("PF_XBTUSD", cartridge["symbol"])
        self.assertEqual("4h", cartridge["tf"])
        self.assertEqual("ichi_v0_baseline", cartridge["baseline_ref"])
        self.assertEqual("cloud_bias", cartridge["entry_rules"]["mode"])
        self.assertEqual(["long", "short"], cartridge["entry_rules"]["allowed_sides"])
        self.assertEqual("none", cartridge["entry_rules"]["require_tk_state"])
        self.assertFalse(cartridge["entry_rules"]["require_chikou_confirmation"])
        self.assertEqual("bias_flip", cartridge["exit_rules"]["mode"])
        self.assertEqual({"type": "none", "params": {}}, cartridge["regime"])
        self.assertEqual(12, cartridge["kill_criteria"]["min_trades"])
        self.assertIn("Eval MUST use --tf 4h", cartridge["kill_criteria"]["notes"])
        self.assertIn("Require stored 4h.jsonl; no 1h fallback", cartridge["kill_criteria"]["notes"])

    def test_phase2_ablation_cartridges_load_requested_components(self):
        ab0 = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_ab0_xbt_v0.yaml")
        full = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_abfull_xbt_v0.yaml")
        no_adx = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_abnoadx_xbt_v0.yaml")
        no_width = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_abnowidth_eth_v0.yaml")
        no_htf = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_abnohtf_eth_v0.yaml")
        no_dwell = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_abnodwell_eth_v0.yaml")

        for cartridge in (ab0, full, no_adx, no_width, no_htf, no_dwell):
            with self.subTest(cartridge=cartridge["id"]):
                self.assertEqual("draft", cartridge["status"])
                self.assertEqual(20, cartridge["ichimoku"]["tenkan"])
                self.assertEqual(60, cartridge["ichimoku"]["kijun"])
                self.assertEqual("bias_flip", cartridge["exit_rules"]["mode"])
                self.assertEqual(
                    "atr_normalized_total_return",
                    cartridge["kill_criteria"]["baseline_metric"],
                )
                self.assertIn("70/30 fee-on OOS", cartridge["kill_criteria"]["notes"])
                self.assertIn("honest trial N", cartridge["notes"])

        self.assertFalse(ab0["regime"]["params"]["phase2_ablation"]["enabled"])
        self.assertEqual(
            {
                "adx_di": True,
                "kumo_width_atr": True,
                "htf_veto": True,
                "dwell_hysteresis": True,
            },
            full["regime"]["params"]["phase2_ablation"]["components"],
        )
        self.assertFalse(no_adx["regime"]["params"]["phase2_ablation"]["components"]["adx_di"])
        self.assertFalse(
            no_width["regime"]["params"]["phase2_ablation"]["components"]["kumo_width_atr"]
        )
        self.assertFalse(no_htf["regime"]["params"]["phase2_ablation"]["components"]["htf_veto"])
        self.assertFalse(
            no_dwell["regime"]["params"]["phase2_ablation"]["components"]["dwell_hysteresis"]
        )

    def test_validate_rejects_invalid_phase2_ablation_component(self):
        valid = load_cartridge(CARTRIDGE_ROOT / "ichi_p2_abfull_xbt_v0.yaml")
        invalid = dict(valid)
        invalid["regime"] = {
            "type": "none",
            "params": {
                "phase2_ablation": {
                    "enabled": True,
                    "label": "AB-bad",
                    "components": {
                        "adx_di": "off",
                        "kumo_width_atr": True,
                        "htf_veto": True,
                        "dwell_hysteresis": True,
                    },
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "adx_di"):
            validate_cartridge(invalid)

    def test_validate_rejects_unknown_status(self):
        valid = load_cartridge(CARTRIDGE_ROOT / "ichi_v0_baseline.yaml")
        invalid = dict(valid)
        invalid["status"] = "live"

        with self.assertRaisesRegex(ValueError, "status"):
            validate_cartridge(invalid)


if __name__ == "__main__":
    unittest.main()
