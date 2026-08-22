# Aura paper trial ledger

Curator-freeze bank for CoS dexter paper runs. This ledger is the source of
truth for the two banked trials below; no new entry families are introduced
here. Curator freeze lifts only after this bank lands.

Run context is repeated on every row as required. Full rows used
`--regime-tf 4h --regime-htf 1d --fee-bps 4`; OOS rows also used
`--oos-split 0.7`. All rows are `tf` 1h, HEAD `e70ce17`, host dexter paper.

## 2026-08-22 banked trials

### Full-sample rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_tk_strong_trend_only_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | e70ce17 | dexter paper | trades 54; WR 0.4259; pnl_fee +2637.6; max_dd 2094; pnl_raw 5904 | n/a full row | killed | CoS verdict NOT A KEEP. Full-sample fee-on positive result did not survive OOS. |
| 2026-08-22 | `ichi_tk_strong_trend_only_v0` | PF_ETHUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | e70ce17 | dexter paper | trades 53; WR 0.5094; pnl_fee -1.56888; max_dd 95.4; pnl_raw 107.8 | n/a full row | killed | CoS verdict NOT A KEEP. ETH was effectively flat/fee-negative. |
| 2026-08-22 | `ichi_kijun_bounce_trend_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | e70ce17 | dexter paper | trades 127; WR 0.3622; pnl_fee -6316.7388; max_dd 3645; pnl_raw 1089 | n/a full row | killed | CoS verdict NOT A KEEP. Full-sample fee-on result was negative. |
| 2026-08-22 | `ichi_kijun_bounce_trend_v0` | PF_ETHUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | e70ce17 | dexter paper | trades 126; WR 0.4524; pnl_fee -36.49448; max_dd 108.1; pnl_raw 240.8 | n/a full row | killed | CoS verdict NOT A KEEP. ETH full-sample fee-on result was negative. |

### Chronological OOS rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_tk_strong_trend_only_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | e70ce17 | dexter paper | IS: trades 35; WR 0.5429; pnl_fee +5827.93; max_dd 1628. OOS: trades 17; WR 0.2353; pnl_fee -2404.5432; max_dd 1603 | false | killed | CoS verdict NOT A KEEP. BTC OOS last 30 percent failed fee-on. |
| 2026-08-22 | `ichi_tk_strong_trend_only_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | e70ce17 | dexter paper | IS: trades 34; WR 0.4412; pnl_fee -62.663; max_dd 95.4. OOS: trades 18; WR 0.6111; pnl_fee +41.84248; max_dd 17.3 | false | killed | CoS verdict NOT A KEEP. ETH OOS did not rescue the banked trial. |
| 2026-08-22 | `ichi_kijun_bounce_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | e70ce17 | dexter paper | IS: 78t; pnl_fee -1181.6696. OOS: 44t; pnl_fee -5018.7444 | true | killed | CoS verdict NOT A KEEP. It beat a worse `ichimoku_v0` baseline only; beating a worse baseline is not a keep while still fee-negative. |
| 2026-08-22 | `ichi_kijun_bounce_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | e70ce17 | dexter paper | IS: 86t; pnl_fee -124.37544. OOS: 40t; pnl_fee +115.9348 | false | killed | CoS verdict NOT A KEEP. ETH OOS gate failed. |
