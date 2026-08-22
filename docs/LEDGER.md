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

## 2026-08-22 R3 Curator statuses

Curator-confirmed R3 status bank for CoS dexter paper rows at HEAD
`a36bc9c`. Full rows used
`--regime-tf 4h --regime-htf 1d --fee-bps 4`; OOS rows also used
`--oos-split 0.7`. All rows are `tf` 1h, host dexter paper. This section
banks statuses only: no new families, no live scopes, no onchain, no lower-TF,
and no funding-in-regime changes.

### R3 full-sample rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | a36bc9c | dexter paper | trades 141; WR 0.3688; pnl_fee +32063.2312 | n/a full row | kept | Kept provisional paper only; not live. ETH secondary OOS fail and DD large keep this paper-only. |
| 2026-08-22 | `ichi_tk_cross_trend_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | a36bc9c | dexter paper | trades 77; pnl_fee +2267.8024; WR 0.4805 | n/a full row | killed | Full positive row did not rescue failed OOS; not collapsed to killed strong parent prior 54t. |
| 2026-08-22 | `ichi_kumo_break_trend_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | a36bc9c | dexter paper | trades 121; pnl_fee -9792.4704; WR 0.4380 | n/a full row | killed | Full-sample fee-on result was negative. |

### R3 chronological OOS rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | a36bc9c | dexter paper | IS: trades 95; WR 0.3474; pnl_fee +18923.8976; max_dd 15143. OOS: trades 44; WR 0.4318; pnl_fee +13287.2384; max_dd 11757 | true | kept | Kept provisional paper only; not live. BTC OOS passed, but DD is large. |
| 2026-08-22 | `ichi_params_20_60_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | a36bc9c | dexter paper | IS: trades 88; WR 0.3636; pnl_fee +478.55764; max_dd 1269.5. OOS: trades 45; WR 0.3778; pnl_fee -107.77412; max_dd 883.5 | false | kept | ETH secondary OOS fail; DD large; paper keep only / not live. |
| 2026-08-22 | `ichi_tk_cross_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | a36bc9c | dexter paper | IS: 53t; WR 0.5472; pnl_fee +5210.2856; max_dd 2159. OOS: 22t; WR 0.3182; pnl_fee -2854.5036; max_dd 1480 | false | killed | CoS/Curator status killed; BTC OOS fee-on failed. |
| 2026-08-22 | `ichi_tk_cross_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | a36bc9c | dexter paper | IS: 45t; WR 0.3778; pnl_fee -265.17032; max_dd 243.4. OOS: 20t; WR 0.55; pnl_fee +17.1472; max_dd 34.7 | false | killed | CoS/Curator status killed; ETH OOS gate failed and did not rescue BTC. |
| 2026-08-22 | `ichi_kumo_break_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | a36bc9c | dexter paper | IS: 75t; WR 0.4533; pnl_fee -2121.5732; max_dd 1337. OOS: 42t; WR 0.4286; pnl_fee -7888.8468; max_dd 5076 | false | killed | CoS/Curator status killed; BTC fee-on failed both halves. |
| 2026-08-22 | `ichi_kumo_break_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | a36bc9c | dexter paper | IS: 79t; WR 0.3797; pnl_fee -236.57568; max_dd 198.2. OOS: 28t; WR 0.6429; pnl_fee -134.27544; max_dd 240.9 | false | killed | CoS/Curator status killed; ETH OOS gate failed and stayed fee-negative. |
