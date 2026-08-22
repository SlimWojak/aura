# Aura paper trial ledger

Curator-freeze bank for CoS dexter paper runs. This ledger is the source of
truth for the banked trials below; no new entry families are introduced here.
Curator freeze lifts only after this bank lands.

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

## 2026-08-22 R4 Curator statuses

Curator-confirmed R4 status bank for exact CoS dexter paper rows at HEAD
`439e16d`. Full rows used
`--regime-tf 4h --regime-htf 1d --fee-bps 4`; OOS rows also used
`--oos-split 0.7`. All rows are `tf` 1h, host dexter paper. This section
banks statuses only: no new families, no live scopes, no constellation/RIVER,
no regime/funding/onchain changes, and no lower-TF changes.

### R4 full-sample rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_eth_dd_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | 439e16d | dexter paper | trades 141; pnl_fee +32063.2312; max_dd 18630; WR 0.3688 | n/a full row | killed | ETH OOS required for this id and failed; identical BTC to parent keep. |
| 2026-08-22 | `ichi_params_10_30_trend_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | 439e16d | dexter paper | trades 195; pnl_fee +1885.8104; max_dd 21695; WR 0.3231 | n/a full row | killed | Thin BTC OOS plus ETH fail; does not displace 20/60 keep. |
| 2026-08-22 | `ichi_tenkan_bounce_trend_v0` | PF_XBTUSD | full | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4` | 439e16d | dexter paper | trades 282; pnl_fee -22285.6836; max_dd 11770; WR 0.4468 | n/a full row | killed | Fee-on negative; distinct from kijun (282 vs 127). |

### R4 chronological OOS rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_eth_dd_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | 439e16d | dexter paper | IS: 95t; WR 0.3474; pnl_fee +18923.8976; max_dd 15143. OOS: 44t; WR 0.4318; pnl_fee +13287.2384; max_dd 11757 | true | killed | ETH OOS required for this id and failed; identical BTC to parent keep. |
| 2026-08-22 | `ichi_params_20_60_trend_eth_dd_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | 439e16d | dexter paper | IS: 88t; WR 0.3636; pnl_fee +478.55764; max_dd 1269.5. OOS: 45t; WR 0.3778; pnl_fee -107.77412; max_dd 883.5 | false | killed | ETH OOS required for this id and failed; identical BTC to parent keep. |
| 2026-08-22 | `ichi_params_10_30_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | 439e16d | dexter paper | IS: 128t; WR 0.3438; pnl_fee +3125.0568; max_dd 9374. OOS: 61t; WR 0.2787; pnl_fee +444.278; max_dd 13012 | true | killed | Thin BTC OOS plus ETH fail; does not displace 20/60 keep. |
| 2026-08-22 | `ichi_params_10_30_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | 439e16d | dexter paper | IS: 133t; WR 0.2782; pnl_fee -39.93656; max_dd 933.6. OOS: 48t; WR 0.2708; pnl_fee +176.28136; max_dd 640.6 | false | killed | Thin BTC OOS plus ETH fail; does not displace 20/60 keep. |
| 2026-08-22 | `ichi_tenkan_bounce_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | 439e16d | dexter paper | IS: 177t; WR 0.4633; pnl_fee -3836.6032; max_dd 2659. OOS: 93t; WR 0.4409; pnl_fee -16173.126; max_dd 11705 | false | killed | Fee-on negative; distinct from kijun (282 vs 127). |
| 2026-08-22 | `ichi_tenkan_bounce_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | 439e16d | dexter paper | IS: 191t; WR 0.4974; pnl_fee -525.65524; max_dd 369.1. OOS: 84t; WR 0.4643; pnl_fee -478.87932; max_dd 538.5 | false | killed | Fee-on negative; distinct from kijun (282 vs 127). |

## 2026-08-22 R5 Curator statuses

Curator-confirmed R5 status bank for exact CoS dexter paper rows at HEAD
`df9182a`. Rows used
`--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7`.
All rows are `tf` 1h, host dexter paper. This section banks statuses only:
no new families, no live scopes, no constellation/RIVER, no
regime/funding/onchain changes, and no lower-TF changes. The parent
`ichi_params_20_60_trend_v0` remains kept.

### R5 chronological OOS rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_timestop_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | df9182a | dexter paper | IS: 103t; WR 0.3592; pnl_fee +20139.3588; max_dd 14252. OOS: 47t; WR 0.4681; pnl_fee +13663.2796; max_dd 11757 | false | killed | BTC IS DD >12000; OOS DD not better than parent. |
| 2026-08-22 | `ichi_params_20_60_trend_timestop_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | df9182a | dexter paper | IS: 96t; WR 0.3542; pnl_fee +233.8314; max_dd 1379.6. OOS: 49t; WR 0.3673; pnl_fee -212.04224; max_dd 883.5 | false | killed | ETH OOS fail. |
| 2026-08-22 | `ichi_params_20_60_trend_long_only_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | df9182a | dexter paper | IS: 71t; WR 0.3521; pnl_fee +13097.1364; max_dd 13353. OOS: 9t; WR 0.4444; pnl_fee +5557.8948; max_dd 6839 | false | killed | OOS trades 9 < min 10; IS DD >12000. |
| 2026-08-22 | `ichi_params_20_60_trend_long_only_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | df9182a | dexter paper | IS: 47t; WR 0.4255; pnl_fee +1247.10912; max_dd 762.6. OOS: 17t; WR 0.1765; pnl_fee -500.28616; max_dd 783.6 | false | killed | ETH OOS fail. |
| 2026-08-22 | `ichi_params_20_60_trend_regime_exit_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | df9182a | dexter paper | IS: 109t; WR 0.3761; pnl_fee +8252.8276; max_dd 15064. OOS: 54t; WR 0.4444; pnl_fee -1552.9392; max_dd 12340 | false | killed | BTC OOS fee-negative and DD >12000. |
| 2026-08-22 | `ichi_params_20_60_trend_regime_exit_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--regime-tf 4h --regime-htf 1d --fee-bps 4 --oos-split 0.7` | df9182a | dexter paper | IS: 95t; WR 0.4; pnl_fee +85.35216; max_dd 1204.1. OOS: 47t; WR 0.3617; pnl_fee -468.23276; max_dd 860.0 | false | killed | ETH fail. |

## 2026-08-22 R6 Curator statuses

Curator-confirmed R6 status bank for exact CoS dexter paper rows at HEAD
`b69e633`, host dexter `~/aura`, `AURA_ROOT=/var/aura`. Rows used
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only`.
This section banks statuses only: no new cartridges, no live scopes, no
constellation/RIVER, no onchain, no lower-TF, no funding-in-classifier changes,
no confirm-wiring edits, and no Intern unlock. The parent
`ichi_params_20_60_trend_v0` remains kept as provisional paper only; no
previously killed id is revived.

### R6 chronological OOS rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_btc_confirm_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only` | b69e633 | dexter paper | IS: 36t; pnl_fee +766.48; max_dd 507.5. OOS: 28t; pnl_fee +340.61; max_dd 753.1 | false | killed | OOS loses to fee-on regime-gated ETH baseline +420.02. IS beats baseline and OOS is positive; BTC confirm is not a no-op versus parent ETH 20/60 (36/28 trades versus 88/45), but must-beat OOS baseline fails. |
| 2026-08-22 | `ichi_v0_trend_eth_primary_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only` | b69e633 | dexter paper | IS: 130t; pnl_fee +298.36; max_dd 857.2. OOS: 51t; pnl_fee +420.02; max_dd 624.0 | false | killed | Identical to regime-gated `ichi_v0_baseline` under same gates; cannot beat baseline. IS max_dd 857.2 > 500 gate. |
| 2026-08-22 | `ichi_params_20_60_trend_long_only_n8_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only` | b69e633 | dexter paper | IS: 71t; pnl_fee +13097.14; max_dd 13353. OOS: 9t; pnl_fee +5557.89; max_dd 6839 | false | killed | BTC OOS beats XBT baseline and OOS DD <=12000, but IS max_dd 13353 >12000 fails the IS gate. |
| 2026-08-22 | `ichi_params_20_60_trend_long_only_n8_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only` | b69e633 | dexter paper | IS: 47t; pnl_fee +1247.11; max_dd 762.6. OOS: 17t; pnl_fee -500.29; max_dd 783.6 | false | killed | ETH OOS is negative and loses to ETH baseline +420.02. This new id fails cartridge kill notes and does not revive the prior killed long_only id. |

### R6 unchanged reference rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only` | b69e633 | dexter paper | IS: 88t; pnl_fee +478.56; max_dd 1269.5. OOS: 45t; pnl_fee -107.77; max_dd 883.5 | false | kept | Parent keep stays provisional paper; A does not supersede this kept id and this section does not mutate its cartridge. |
| 2026-08-22 | `ichi_v0_baseline` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --metrics-only` | b69e633 | dexter paper | IS: 130t; pnl_fee +298.36; max_dd 857.2. OOS: 51t; pnl_fee +420.02; max_dd 624.0 | n/a baseline ref | queued | Fee-on regime-gated ETH baseline reference for R6 comparisons; status is not changed. |

## 2026-08-22 Track A keep rescore

CoS/Curator Track A rescore for provisional keep
`ichi_params_20_60_trend_v0` at HEAD `dcc6dc6`, host dexter
`AURA_ROOT=/var/aura`. Rows used
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only`.
Evidence path:
`/var/aura/evidence/evals/track-a-rescore-20260822/`.
This section banks the rescore only: no cartridge status mutation, no new
cartridges, no live scopes, no constellation/RIVER, and no previously killed id
is revived. The parent YAML remains `kept` as provisional paper pending human
forever-kill decision.

### Track A rescore rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | dcc6dc6 | dexter paper | IS: ATR total 39.89; Sharpe 0.697; PSR 0.858; DSR 0.146; Calmar 0.517; maxDD -33.05; trades 95; legacy pnl_fee +18923.90; maxDD pts 15143. OOS: ATR total 27.45; Sharpe 1.109; PSR 0.866; DSR 0.155; Calmar 1.878; maxDD -14.77; trades 44; legacy pnl_fee +13287.24; maxDD pts 11757 | true | provisional-fail | BTC OOS beats baseline ATR and old OOS gate, but Track A requires DSR >0.95, PBO <0.10, and beating baseline on both symbols. |
| 2026-08-22 | `ichi_params_20_60_trend_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | dcc6dc6 | dexter paper | IS: ATR total 24.59; Sharpe 0.426; PSR 0.744; DSR 0.071; Calmar 0.313; maxDD -33.65; trades 88; legacy pnl_fee +478.56. OOS: ATR total -2.95; Sharpe -0.117; PSR 0.454; DSR 0.013; Calmar -0.105; maxDD -28.34; trades 45; legacy pnl_fee -107.77 | false | provisional-fail | ETH OOS fails the old gate, loses to baseline ATR, and keeps the parent below the Track A both-symbol requirement. |

### Track A baseline references

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_v0_baseline` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | dcc6dc6 | dexter paper | OOS: ATR total 0.033; DSR 0.017; trades 65; legacy pnl_fee -2000.15 | n/a baseline ref | reference | BTC baseline for same-metric Track A comparison. |
| 2026-08-22 | `ichi_v0_baseline` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | dcc6dc6 | dexter paper | OOS: ATR total 15.05; DSR 0.094; trades 51; legacy pnl_fee +420.02 | n/a baseline ref | reference | ETH baseline beats the provisional keep on OOS ATR and legacy fee PnL. |

### Track A PBO matrix

| Date | Universe | Metric | CSCV groups | Runnable paths | N_honest | PBO | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | BTC | atr_normalized | 8 | 8 | 34 | 0.1143 | provisional-fail | Fails strict PBO <0.10 gate. Runnable PBO universe was 8 paths, not the full 34 trial count. |
| 2026-08-22 | ETH | atr_normalized | 8 | 8 | 34 | 0.5143 | provisional-fail | Fails PBO <0.10 and ETH OOS baseline comparison. Runnable PBO universe was 8 paths, not the full 34 trial count. |
| 2026-08-22 | Mixed BTC+ETH | atr_normalized | 8 | 16 | 34 | 0.4143 | provisional-fail | Mixed-symbol matrix fails PBO <0.10. Runnable PBO universe was 16 paths from 8 BTC plus 8 ETH paths, not the full 34 trial count. |

Track A gate for this bank is `DSR > 0.95 AND PBO < 0.10 AND beats baseline
ATR on BOTH symbols`. CoS/Curator disposition is **provisional-fail**. The
cartridge remains a provisional paper `kept` YAML until a human forever-kill
decision.

## 2026-08-22 Track C exit-vocabulary bake-off

CoS/Curator Track C exit-vocabulary status bank for exact dexter paper rows at
HEAD `9d53c79`, host dexter, `AURA_ROOT=/var/aura`. Rows used
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only`.
Evidence path:
`/var/aura/evidence/evals/track-c-exit-vocab-20260822/`.
This section banks three new ids as forever-killed: no new exits, no regime
ablation, no live scopes, no constellation/RIVER, no lower-TF changes, and no
previously killed id is revived. The parent `ichi_params_20_60_trend_v0`
remains `kept` as provisional paper only.

Track C kill criteria: forced 70/30 fee-on OOS must beat parent
`ichi_params_20_60_trend_v0` on `atr_normalized_total_return`; ATR maxDD must
not exceed parent by more than 10% on either split; `min_trades >= 12`.

### Track C chronological OOS rows

| Date | Cartridge id | Symbols | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_v0_trend_kijun_trail_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | 9d53c79 | dexter paper | XBT OOS ATR total 17.38 < parent 27.45. ETH OOS ATR total -9.10 < parent -2.95; ETH OOS DD 1.17x parent. IS Calmar/maxDD improved both symbols. | false | killed | Forever-killed. OOS return loses despite IS Calmar/maxDD improvement, and ETH OOS DD breaches the parent +10% limit. |
| 2026-08-22 | `ichi_v0_trend_chandelier_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | 9d53c79 | dexter paper | OOS ATR deeply negative on both symbols; DD breaches. | false | killed | Forever-killed. OOS ATR and DD both fail the Track C gate. |
| 2026-08-22 | `ichi_v0_trend_atr_stop_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 34 --metrics-only` | 9d53c79 | dexter paper | XBT OOS ATR total 36.61 > parent 27.45, but trades 4 < 12 and DD catastrophic. ETH fails. | false | killed | Forever-killed. A single XBT OOS ATR beat cannot pass with too few trades, catastrophic DD, and ETH failure. |

## 2026-08-22 Phase-2 regime ablation bake-off

CoS Phase-2 ablation bank for exact dexter paper rows at HEAD `23ea168`, host
dexter, `AURA_ROOT=/var/aura`. Rows used
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only`.
Evidence path:
`/var/aura/evidence/evals/phase2-ablation-20260822/`.

This section banks evidence and dispositions only: no production
`RegimeParams` default changes, no live scopes, no constellation/RIVER, no
runtime state, no lower-TF changes, and no status mutation for
`ichi_params_20_60_trend_v0`. The twelve ablation cartridges remain draft
research cartridges in repo; finished-ablation dispositions are recorded here
instead of forever-killing the ablation ids.

### Phase-2 ablation OOS rows

| Date | Ablation | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | AB-0 | `ichi_p2_ab0_xbt_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 74.54; Sharpe 1.42; DSR 0.406; Calmar 2.116; maxDD -35.62; trades 261; pnl_fee +18762 | n/a ablation ref | reference | No-Phase-2-veto baseline. Beats AB-FULL OOS Calmar and DSR on XBT; not promoted to production by this bank. |
| 2026-08-22 | AB-0 | `ichi_p2_ab0_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 27.09; Sharpe 0.51; DSR 0.124; Calmar 0.499; maxDD -54.92; trades 279; pnl_fee +78 | n/a ablation ref | reference | No-Phase-2-veto baseline. Beats AB-FULL OOS Calmar and DSR on ETH; full gate may be net harmful as a package. |
| 2026-08-22 | AB-FULL | `ichi_p2_abfull_xbt_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 27.45; Sharpe 1.11; DSR 0.289; Calmar 1.878; maxDD -14.77; trades 44; pnl_fee +13287 | n/a ablation ref | reference | Full production-spine gate reference: ADX/DI, kumo width/ATR, 1d HTF veto, and dwell/hysteresis all enabled. |
| 2026-08-22 | AB-FULL | `ichi_p2_abfull_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total -2.95; Sharpe -0.12; DSR 0.037; Calmar -0.105; maxDD -28.34; trades 45; pnl_fee -108 | n/a ablation ref | reference | Full production-spine gate reference. ETH OOS is negative, so this row does not support auto-promotion. |
| 2026-08-22 | AB-noADX | `ichi_p2_abnoadx_xbt_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 51.80; Sharpe 1.63; DSR 0.501; Calmar 2.490; maxDD -21.03; trades 66; pnl_fee +20273 | n/a ablation | DROP_CANDIDATE | Removing ADX/DI improves OOS Calmar and DSR versus AB-FULL on XBT. |
| 2026-08-22 | AB-noADX | `ichi_p2_abnoadx_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 31.92; Sharpe 1.00; DSR 0.255; Calmar 1.028; maxDD -31.41; trades 62; pnl_fee +526 | n/a ablation | DROP_CANDIDATE | Removing ADX/DI improves OOS Calmar and DSR versus AB-FULL on ETH. |
| 2026-08-22 | AB-noWidth | `ichi_p2_abnowidth_xbt_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 31.83; Sharpe 1.15; DSR 0.302; Calmar 1.817; maxDD -17.71; trades 48; pnl_fee +10842 | n/a ablation | INCONCLUSIVE | Removing kumo width/ATR modestly improves DSR but slightly worsens Calmar versus AB-FULL on XBT. |
| 2026-08-22 | AB-noWidth | `ichi_p2_abnowidth_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 9.01; Sharpe 0.32; DSR 0.089; Calmar 0.292; maxDD -31.25; trades 50; pnl_fee +19 | n/a ablation | INCONCLUSIVE | Removing kumo width/ATR improves ETH versus AB-FULL, but XBT evidence is mixed. |
| 2026-08-22 | AB-noHTF | `ichi_p2_abnohtf_xbt_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 8.05; Sharpe 0.30; DSR 0.086; Calmar 0.341; maxDD -23.90; trades 54; pnl_fee +5342 | n/a ablation | KEEP_IN_SPINE | Removing the 1d HTF veto worsens Calmar and DSR versus AB-FULL on XBT. |
| 2026-08-22 | AB-noHTF | `ichi_p2_abnohtf_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total -12.89; Sharpe -0.48; DSR 0.016; Calmar -0.400; maxDD -32.58; trades 54; pnl_fee -327 | n/a ablation | KEEP_IN_SPINE | Removing the 1d HTF veto worsens Calmar and DSR versus AB-FULL on ETH. |
| 2026-08-22 | AB-noDwell | `ichi_p2_abnodwell_xbt_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 56.08; Sharpe 1.84; DSR 0.591; Calmar 1.995; maxDD -28.42; trades 50; pnl_fee +19130 | n/a ablation | DROP_CANDIDATE | Removing dwell/hysteresis improves OOS Calmar and DSR versus AB-FULL on XBT. |
| 2026-08-22 | AB-noDwell | `ichi_p2_abnodwell_eth_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 12 --metrics-only` | 23ea168 | dexter paper | OOS: ATR total 22.34; Sharpe 0.73; DSR 0.176; Calmar 0.711; maxDD -31.76; trades 54; pnl_fee +726 | n/a ablation | DROP_CANDIDATE | Removing dwell/hysteresis improves OOS Calmar and DSR versus AB-FULL on ETH. |

### Phase-2 component verdicts

| Component | Ablation comparison | CoS verdict | Evidence summary | Repo action |
|---|---|---|---|---|
| 1d higher-timeframe veto | AB-noHTF vs AB-FULL | KEEP_IN_SPINE | Removal worsens OOS Calmar on both symbols: XBT 0.341 vs 1.878, ETH -0.400 vs -0.105; DSR also worsens both. | Keep documented as spine evidence; no production default mutation in this PR. |
| ADX/DI | AB-noADX vs AB-FULL | DROP_CANDIDATE | Removal improves OOS Calmar and DSR on both symbols: XBT Calmar 2.490 vs 1.878, ETH 1.028 vs -0.105. | Bank as thinning candidate for a separate human/CoS decision. |
| Dwell/hysteresis | AB-noDwell vs AB-FULL | DROP_CANDIDATE | Removal improves OOS Calmar and DSR on both symbols: XBT DSR 0.591 vs 0.289, ETH 0.176 vs 0.037. | Bank as thinning candidate for a separate human/CoS decision. |
| Kumo width/ATR | AB-noWidth vs AB-FULL | INCONCLUSIVE | ETH improves, while XBT DSR improves slightly and Calmar slips from 1.878 to 1.817. | Leave for further evidence; no default mutation. |
| Full Phase-2 gate package | AB-0 vs AB-FULL | reference | AB-0 beats AB-FULL OOS Calmar and DSR on both symbols, suggesting the full gate may be net harmful as a package. | Do not promote ungated behavior to production in this PR; bank evidence only. |

## 2026-08-22 R7 thin-spine Intern bake-off

CoS/Curator R7 thin-spine Intern status bank for exact dexter paper rows at
HEAD `702b6c5`, host dexter, `AURA_ROOT=/var/aura`. Rows used thin Phase-2
defaults: HTF+width on, ADX/dwell off, with flags
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only`.
Evidence path:
`/var/aura/evidence/evals/r7-thin-spine-20260822/`.

This section banks three R7 research ids and the same-flag thin baseline
references only. It does not mutate `ichi_params_20_60_trend_v0`, which remains
kept / Track A provisional-fail; it does not change runtime defaults, widen
Kraken scopes, add live behavior, write runtime state, touch constellation/RIVER,
or revive any killed id.

Thin-spine baseline reference rows are not the Track A full-spine baseline
rows. Track A used the full production spine and reported baseline OOS ATR
references of XBT `0.033` and ETH `15.05`; R7 comparisons use this bank's
HTF+width-only thin baseline rerun below.

### R7 thin-spine baseline references

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_v0_baseline` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 702b6c5 | dexter paper | IS: ATR total 43.74; trades 259. OOS: ATR total -7.33; trades 105. | n/a baseline ref | reference | Thin-spine same-flag baseline for R7 XBT comparisons; differs from Track A full-spine baseline. |
| 2026-08-22 | `ichi_v0_baseline` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 702b6c5 | dexter paper | IS: ATR total 133.30; trades 238. OOS: ATR total 38.02; trades 95. | n/a baseline ref | reference | Thin-spine same-flag baseline for R7 ETH comparisons; differs from Track A full-spine baseline. |

### R7 cartridge dispositions

| Date | Cartridge id | Symbols | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_kumo_break_thin_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 702b6c5 | dexter paper | XBT IS ATR -15.91 < thin baseline 43.74. XBT OOS ATR -1.92 > thin baseline -7.33, but IS failed the IS+OOS beat gate. ETH also failed. | false | killed | Killed forever. Do not revive `ichi_kumo_break_thin_v0` or the older killed `ichi_kumo_break_trend_v0`. |
| 2026-08-22 | `ichi_always_on_tsmom_thin_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 702b6c5 | dexter paper | XBT IS ATR 64.55 and OOS ATR 4.60 beat thin baseline 43.74 and -7.33. ETH OOS ATR 34.92 lost to thin baseline 38.02. maxDD pts OK. | true on XBT | kept | Kept provisional paper only; not live. Same BTC-primary scar pattern as prior keeps; ETH remains secondary context. |
| 2026-08-22 | `ichi_cloud_bias_tsmom_thin_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 702b6c5 | dexter paper | XBT IS/OOS ATR 120.35/60.65 beat thin baseline 43.74/-7.33. ETH IS/OOS ATR 190.88/97.61 beat thin baseline 133.30/38.02. Not no-op versus always_on: XBT trades 362 vs 338, overlap 78. | true | kept | Kept provisional paper only; not live. Strongest R7 candidate, but no autopromote. |

## 2026-08-22 R7 DSR/PBO honesty rescore

CoS/Curator R7 DSR/PBO honesty rescore for provisional paper keeps
`ichi_always_on_tsmom_thin_v0` and `ichi_cloud_bias_tsmom_thin_v0` at commit
`5005ba3d9ed11f18bc7a686ef056787c83b50438`, host dexter,
`AURA_ROOT=/var/aura`. Rows used the thin Phase-2 spine: HTF+width on,
ADX/dwell off, with flags
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only`.
Evidence path:
`/var/aura/evidence/evals/r7-dsr-pbo-20260822/`.

This section banks the honesty rescore only: no cartridge status mutation, no
new cartridges, no live scopes, no constellation/RIVER, no runtime state, and
no previously killed id is revived. The two R7 keep YAML statuses remain
`kept` as provisional paper only; no forever-kill decision is recorded here.
`ichi_kumo_break_thin_v0` remains killed, and
`ichi_params_20_60_trend_v0` is untouched.

### R7 DSR/PBO baseline references

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_v0_baseline` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 5005ba3 | dexter paper | OOS: ATR total -7.3311; DSR 0.0071 | n/a baseline ref | reference | Thin-spine baseline for R7 honesty comparison. |
| 2026-08-22 | `ichi_v0_baseline` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 5005ba3 | dexter paper | OOS: ATR total 38.0179; DSR 0.2434 | n/a baseline ref | reference | Thin-spine baseline for R7 honesty comparison. |

### R7 DSR/PBO rescore rows

| Date | Cartridge id | Symbol | Split | tf | Flags | HEAD | Host | Metrics | Track A gate | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_always_on_tsmom_thin_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 5005ba3 | dexter paper | OOS: ATR total 4.5977 beats thin baseline -7.3311; DSR 0.0236 | false | provisional-fail | DSR fails `> 0.95`; candidate also fails the both-symbol gate because ETH loses to the thin baseline and ETH/Mixed PBO fail. YAML remains `kept` provisional paper only. |
| 2026-08-22 | `ichi_always_on_tsmom_thin_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 5005ba3 | dexter paper | OOS: ATR total 34.9233 loses to thin baseline 38.0179; DSR 0.2027 | false | provisional-fail | DSR fails `> 0.95`; ETH OOS ATR loses to baseline and ETH PBO fails. YAML remains `kept` provisional paper only. |
| 2026-08-22 | `ichi_cloud_bias_tsmom_thin_v0` | PF_XBTUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 5005ba3 | dexter paper | OOS: ATR total 60.6522 beats thin baseline -7.3311; DSR 0.3432 | false | provisional-fail | ATR beats, but DSR fails `> 0.95`; ETH/Mixed PBO fail the Track A gate. YAML remains `kept` provisional paper only. |
| 2026-08-22 | `ichi_cloud_bias_tsmom_thin_v0` | PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only` | 5005ba3 | dexter paper | OOS: ATR total 97.6087 beats thin baseline 38.0179; DSR 0.7289 | false | provisional-fail | ATR beats, but DSR fails `> 0.95` and ETH PBO fails. YAML remains `kept` provisional paper only. |

### R7 DSR/PBO matrix

| Date | Universe | Metric | CSCV groups | Runnable paths | N_honest | PBO | CoS/Curator disposition | Note |
|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | BTC | atr_normalized | 8 | 4 | 37 | 0.0000 | pass | Passes strict PBO <0.10. PBO pass alone is insufficient without DSR >0.95 and both-symbol OOS ATR beat. |
| 2026-08-22 | ETH | atr_normalized | 8 | 4 | 37 | 0.3429 | provisional-fail | Fails strict PBO <0.10. |
| 2026-08-22 | Mixed BTC+ETH | atr_normalized | 8 | 8 | 37 | 0.1286 | provisional-fail | Fails strict PBO <0.10. |

Track A gate for this R7 honesty bank is `DSR > 0.95 AND PBO < 0.10 AND
beats baseline ATR on BOTH symbols`. CoS/Curator disposition is
**provisional-fail** for both `kept` R7 TSMOM cartridges. The cartridge YAML
statuses remain provisional paper `kept`; no forever-kill decision is made, no
live behavior is added, and no killed id is revived.

## 2026-08-22 status hygiene demotion bank

Fable+Grok lateral review closes the misleading provisional `kept` labels without
forever-killing any id. This is paper-only status hygiene: no strategy logic,
regime defaults, live scopes, runtime state, or runner authority changes; no
previously killed id is revived; Intern R8 remains frozen.

Evidence cited from Track A rescore path:
`/var/aura/evidence/evals/track-a-rescore-20260822/`; PR #34 R7 thin-spine bank:
`/var/aura/evidence/evals/r7-thin-spine-20260822/`; and PR #35 R7 DSR/PBO
honesty rescore: `/var/aura/evidence/evals/r7-dsr-pbo-20260822/`.

| Date | Cartridge id | Prior status | New status | Rationale |
|---|---|---|---|---|
| 2026-08-22 | `ichi_params_20_60_trend_v0` | kept | scarred_control | Track A/R7 honesty makes the old keep a provisional-fail: BTC residual evidence remains useful as a control, but ETH, drawdown, DSR/PBO, and both-symbol baseline gates do not support runner status. |
| 2026-08-22 | `ichi_always_on_tsmom_thin_v0` | kept | scarred_control | R7 BTC-primary residual passed, but ETH lost to the thin baseline and PR #35 honesty still failed; retain as a scarred paper control only. |
| 2026-08-22 | `ichi_cloud_bias_tsmom_thin_v0` | kept | champion_control | Best residual R7 ATR control: XBT and ETH beat thin baselines, but PR #35 honesty still failed, so this remains a benchmark/control only, not a runner and not live. |

## 2026-08-22 Track A power-test DETECTABLE

Paper-only CoS power-test bank for the Track A harness at HEAD
`ae6d5b026ffa8b3ac19710e030b469e680f129e3` (PR #38 harness). Evidence:
`/var/aura/evidence/power_tests/20260822/` plus `SUMMARY.md`.

Flags:
`--tf 1h --fee-bps 4 --oos-split 0.7 --trial-count 37 --atr-period 14 --regime-tf 4h --regime-htf 1d`.
Injected edge: `edge_sharpe 0.9`, period-level ATR-normalized.

| Date | Symbol | Synthetic control | Result | CoS verdict note |
|---|---|---|---|---|
| 2026-08-22 | PF_XBTUSD | positive | exit 0; control_passed true; track_a_keep true; DSR 1.0; PBO 0.0; n_paths 37; n_honest 37 | Positive synthetic edge was kept. |
| 2026-08-22 | PF_XBTUSD | negative | exit 0; control_passed true; track_a_keep false; DSR ~0.0154; PBO 1.0; n_paths 37; n_honest 37 | Negative shuffle was rejected. |
| 2026-08-22 | PF_ETHUSD | positive | Same keep pattern as PF_XBTUSD positive; n_paths 37; n_honest 37 | Positive synthetic edge was kept. |
| 2026-08-22 | PF_ETHUSD | negative | Same reject pattern as PF_XBTUSD negative; n_paths 37; n_honest 37 | Negative shuffle was rejected. |

CoS verdict: **DETECTABLE** -- both positives keep synthetic edge; both
negatives reject shuffle. `n_paths == n_honest == 37` on these synthetic runs,
so the PBO scar is explicit and closed for this harness path.

Implications locked: prior cartridge kills remain informative; Intern R8 still
frozen; next is width ON/OFF A/B (Grok path) because the harness can hear. This
PR makes no live change and records no status flips.

## 2026-08-22 width ON/OFF A/B INCONCLUSIVE

Paper-only CoS width ON/OFF A/B bank at eval HEAD `ae6d5b0`; main may be
`6390ba8+`. Evidence path:
`/var/aura/evidence/evals/width-ab-20260822/` (`SUMMARY.md`,
`comparison.json`).

This section banks evidence only: no YAML status changes, no `RegimeParams`
default changes, no live scopes, no constellation/RIVER, no runtime state, and
no Intern R8 unlock. The spine defaults are unchanged.

WIDTH ON is the thin production default spine: HTF+width ON, ADX/dwell OFF, via
normal `--id`. WIDTH OFF is evidence-only `--path` override behavior with
`regime.params.phase2_ablation` setting `kumo_width_atr=false`.

Locked set: `ichi_v0_baseline`, `ichi_params_20_60_trend_v0`
(`scarred_control`), `ichi_always_on_tsmom_thin_v0` (`scarred_control`), and
`ichi_cloud_bias_tsmom_thin_v0` (`champion_control`) across WIDTH ON/OFF and
`PF_XBTUSD` + `PF_ETHUSD` = 16 runs.

Flags:
`--tf 1h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 37 --metrics-only`.

| Measure | PF_XBTUSD | PF_ETHUSD | CoS read |
|---|---|---|---|
| Flip-rate | 0.1626 -> 0.1596 (-1.84% rel) | 0.1463 -> 0.1435 (-1.95% rel) | Noise. |
| `TREND_*` occupancy | 24.55% -> 30.72% (+6.17pp) | 23.97% -> 29.22% (+5.25pp) | Width is not a label no-op. |
| Champion `ichi_cloud_bias_tsmom_thin_v0` OOS ATR | 60.65 -> 74.39 (+13.74) | 97.61 -> 96.09 (-1.52) | Mixed sign. |
| Champion `ichi_cloud_bias_tsmom_thin_v0` DSR | 0.343 -> 0.436 | 0.729 -> 0.655 | Mixed sign. |

CoS disposition: **INCONCLUSIVE** -- neither DROP nor KEEP_IN_SPINE under the
Grok falsifier, because the ATR move is mixed-sign and flip-rate did not move
beyond noise.

Locked implication: production thin spine leaves width ON; no further N is
spent on width. Intern R8 remains frozen. The next planned unscarred shot is 4h
signal/regime-TF entry, not in this PR.

## 2026-08-22 4h regime-TF signal one-shot

Paper-only CoS bank for `ichi_cloud_bias_tsmom_4h_v0` at HEAD `6a4054c`.
Evidence path: `/var/aura/evidence/evals/tf4h-cloud-bias-20260822/`.

Flags:
`--tf 4h --fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 38 --metrics-only`.

Adaptation note: regime labels were sourced from stored 1h OHLCV for the
Phase-2 regime/HTF classifier; trading decisions and PnL stayed on stored 4h
decision bars.

| Date | Cartridge id | Symbols | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `ichi_cloud_bias_tsmom_4h_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 4h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 38 --metrics-only` | 6a4054c | dexter paper | XBT IS ATR 14.01 < baseline 17.31 (lose), OOS 37.57 > 26.32 (beat), trades 109/48. ETH IS 67.82 < 78.56 (lose), OOS 27.49 > -3.95 (beat), trades 96/39. | false | killed forever | IS lost both symbols under the falsifier despite OOS beats; do not revive. |

Disposition: **killed forever** -- IS lose both symbols; do not revive
`ichi_cloud_bias_tsmom_4h_v0`. Intern re-freeze after this bank; no family mill.

## 2026-08-22 funding-in-returns smoke

Paper-only CoS funding-in-returns smoke for the eval harness in PR #43 at HEAD
`f78b22f`. The harness keeps `--apply-funding` default off; when enabled,
held-bar funding is applied into `net_*` metrics.

Evidence path: `/var/aura/evidence/evals/funding-smoke-20260822/`.

Cartridge: `ichi_cloud_bias_tsmom_thin_v0` (`champion_control`) with thin spine
flags and `--trial-count 39`.

Coverage:
- `--since 2025-08-20T08:00:00Z` failed closed with 9 funding gaps.
- Contiguous pull used
  `--since 2026-05-09T07:00:00Z` through `2026-08-22T05:00:00Z`
  (2519 candles); `funding_missing_held_bars=0`.

| Symbol | Fee-only OOS ATR | Fee-only DSR | Fee+funding OOS ATR | Fee+funding DSR | funding_drag_atr | funding_drag_points |
|---|---:|---:|---:|---:|---:|---:|
| XBT | 26.0176 | 0.6704 | 25.8748 | 0.6636 | 0.1428 | 80.81 |
| ETH | 25.6014 | 0.6208 | 25.4097 | 0.6116 | 0.1917 | 3.09 |

CoS verdict: **harness PASS** -- nonzero drag and `net_*` metrics differ. No
cartridge status mutation. Intern remains frozen. Default eval remains fee-only
until CoS opts into funding-on rescores.

Follow-up: funding store gaps exist before May 2026; optional later gap-fill or
longer contiguous pull can extend this evidence.

## 2026-08-22 funding gap-fill

Paper-only CoS funding gap-fill bank. Evidence path:
`/var/aura/evidence/evals/funding-gapfill-20260822/`.

- Action: `market_ingest funding-pull PF_XBTUSD+PF_ETHUSD` from official Kraken
  funding history; no invented zero rates.
- Before 8798 -> after 8802 rows; tip extended to `2026-08-22T10:00:00Z`.
- Residual: 9 official missing hours, identical for `PF_XBTUSD` and
  `PF_ETHUSD`:
  - `2025-08-31T04:00:00Z`
  - `2025-11-01T16:00:00Z`
  - `2025-11-01T17:00:00Z`
  - `2025-11-02T04:00:00Z`
  - `2025-11-19T05:00:00Z`
  - `2025-12-04T09:00:00Z`
  - `2026-02-04T12:00:00Z`
  - `2026-02-13T18:00:00Z`
  - `2026-05-09T06:00:00Z`
- Longest contiguous official span starts at `2026-05-09T07:00:00Z`
  (~2524h).
- Cannot clear holes without fabricating rates; full
  `--since 2025-08-20` still fail-closes.

## 2026-08-22 funding-on controls re-score

Paper-only CoS funding-on controls re-score. Evidence path:
`/var/aura/evidence/evals/funding-rescore-controls-20260822/`.

Run context: HEAD `61351e1`; `--since 2026-05-09T07:00:00Z`; thin spine;
`--trial-count 40`; `funding_missing_held_bars=0`.

| Cartridge id | Symbol | Fee-only OOS ATR | Fee-only DSR | Fee+funding OOS ATR | Fee+funding DSR | funding_drag_atr |
|---|---|---:|---:|---:|---:|---:|
| `ichi_cloud_bias_tsmom_thin_v0` | PF_XBTUSD | 26.0176 | 0.6668 | 25.8748 | 0.6599 | 0.1428 |
| `ichi_cloud_bias_tsmom_thin_v0` | PF_ETHUSD | 25.6014 | 0.6170 | 25.4097 | 0.6077 | 0.1917 |
| `ichi_params_20_60_trend_v0` | PF_XBTUSD | 30.5817 | 0.7761 | 30.3756 | 0.7683 | 0.2061 |
| `ichi_params_20_60_trend_v0` | PF_ETHUSD | 0.1476 | 0.0156 | 0.1102 | 0.0153 | 0.0374 |
| `ichi_always_on_tsmom_thin_v0` | PF_XBTUSD | -0.6254 | 0.0105 | -0.6455 | 0.0104 | 0.0201 |
| `ichi_always_on_tsmom_thin_v0` | PF_ETHUSD | -4.9391 | 0.0005 | -4.9909 | 0.0005 | 0.0517 |

CoS verdict: funding drag is small and causes no status flips. Default eval
remains fee-only; Intern remains frozen. Short-window caveat applies: this is
not full-history Track A.

## 2026-08-22 IC feature screen run

Paper-only CoS IC feature screen bank for the dexter run at harness merge
PR #46 -> HEAD `96dc416`. Evidence path:
`/var/aura/evidence/evals/ic-screen-20260822/` (`report.json`,
`scores.csv`, `SUMMARY.md`, `run.log`).

Command:
```bash
python3 -m runtime.tools.eval_run ic-screen \
  --aura-root /var/aura \
  --symbols PF_XBTUSD,PF_ETHUSD \
  --tf 1h \
  --horizons 4,12,24,48 \
  --atr-period 14 \
  --output-id ic-screen-20260822
```

Harness contract: forward ATR-normalized returns at horizons 4/12/24/48; HAC
CIs for overlapping returns; Benjamini-Hochberg q-values across emitted feature
tests. Kill rule: a feature is dead only when every usable CI spans 0 on both
symbols.

| Bucket | Features | CoS read |
|---|---|---|
| Dead features | `adx`, `flat_kijun_bars`, `flat_spanb_bars`, `flat_tenkan_bars`, `kumo_width_atr`, `tk_spread_atr` | Every usable CI spans 0 on both symbols. Do not spend Track A on these as feature evidence. |
| Both-symbol nonzero-CI survivors | `chikou_gap_atr`, `chikou_proxy`, `cloud_bias`, `di_spread`, `price_cloud_distance_atr`, `price_vs_kumo` | Candidate features only. Surviving this screen is not a Track A pass or cartridge keep. |
| One-symbol-only survivors | `future_twist`, `regime_state`, `thin_kumo`, `tk_align` | Weaker, one-sided evidence. Do not treat as dual-symbol survivors. |

Best BH q-values remain high at about `0.10` to `0.17`; no feature is
conventionally significant at BH `0.05`. This bank records evidence only: no
cartridge YAML/status changes, no cartridge revival, no Intern unlock, no
lower-timeframe ingest, no live scopes, and no Track A loosening. Intern remains
frozen and Track A is unchanged.

## 2026-08-22 enrichment lane IC run

Paper-only CoS enrichment IC feature screen bank at main tip `86d4ca2`.
Evidence path:
`/var/aura/evidence/evals/ic-screen-enrichment-20260822/` (`report.json`,
`scores.csv`, `SUMMARY.md`, `run.log`).

Scope: locked enrichment lane for Daily DR, Daily FVG, Chikou-vs-Daily-DR, and
Daily-FVG/flat-Span-B IC-screen features. Definitions and fence are registered
in `docs/briefs/2026-08-22-enrichment-lane.md`.

Command:
```bash
python3 -m runtime.tools.eval_run ic-screen \
  --aura-root /var/aura \
  --symbols PF_XBTUSD,PF_ETHUSD \
  --tf 1h \
  --horizons 4,12,24,48 \
  --atr-period 14 \
  --feature-set enrichment \
  --output-id ic-screen-enrichment-20260822
```

Harness contract: feature-set `enrichment`; forward ATR-normalized returns at
horizons 4/12/24/48; HAC CIs for overlapping returns; Benjamini-Hochberg
q-values across emitted feature tests. Kill rule remains strict: a feature is
dead only when every usable CI spans 0 on both symbols.

| Bucket | Features | CoS read |
|---|---|---|
| Dead features | `chikou_clears_daily_dr`, `chikou_daily_dr_clearance_atr`, `daily_fvg_distance_atr`, `daily_fvg_price_inside` | Every usable CI spans 0 on both symbols. The rank-1 Chikou x Daily DR thesis is IC-dead; do not mill cartridges on these dead features. |
| Both-symbol nonzero-CI survivors | `daily_dr_side`, `daily_dr_position`, `fvg_flat_spanb_overlap`, `daily_fvg_side` | Candidate features only. Best BH q-values remain about `0.19` to `0.24`, so none clear conventional BH `0.05`. |

CoS disposition: **evidence bank only**. The enrichment lane does not loosen
Track A, unlock Intern, revive killed ids, add lower-timeframe ADDR, change
control statuses, or add live scopes. Next cartridge work should prioritize the
rank-2 Daily FVG/flat-Span-B overlap thesis over dead Chikou x Daily DR
features.

## 2026-08-22 failed DI-expansion bake-off

Binding CoS verdict for `vol_di_expand_trend_v0` at main tip `507d840`.
Evidence path: `/var/aura/evidence/evals/vol-di-expand-20260822/`
(`logs/*.json` plus auto `E-ichi-*` dirs listed in those outputs).

Run context: dexter paper, `AURA_ROOT=/var/aura`, thin Phase-2 spine
(`--regime-tf 4h --regime-htf 1d`, HTF+width ON, ADX/dwell OFF),
`--tf 1h --fee-bps 4 --oos-split 0.7 --atr-period 14 --trial-count 38 --metrics-only`.

Kill rule: `vol_di_expand_trend_v0` had to beat champion
`ichi_cloud_bias_tsmom_thin_v0` on fee-aware OOS ATR-normalized
`total_return` for both symbols. It lost both symbols, so the cartridge is
forever killed.

| Date | Cartridge id | Symbols | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `vol_di_expand_trend_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 38 --metrics-only` | 507d840 | dexter paper | OOS ATR total_return: XBT 1.29 vs champion 60.65; ETH 2.86 vs champion 97.61. | false | killed forever | Loses to `ichi_cloud_bias_tsmom_thin_v0` on both symbols; do not revive. |

Status scope: this bank mutates only `vol_di_expand_trend_v0` to `killed`.
`ichi_cloud_bias_tsmom_thin_v0` remains `champion_control`; scarred controls
remain unchanged. Intern remains frozen, no control status churn, no Track A
loosening, no live scopes, and the 15m survivor-derived follow-on remains
deferred.

## 2026-08-22 failed rank-2 enrichment FVG/flat-Span-B bake-off

Binding CoS verdict for `enrich_fvg_flat_spanb_trend_v0` at main tip
`9fdf1b1`. Evidence path:
`/var/aura/evidence/evals/enrich-fvg-spanb-20260822/` (`logs` plus
`cos-verdict.json`).

Run context: dexter paper, `AURA_ROOT=/var/aura`, thin Phase-2 spine
(`--regime-tf 4h --regime-htf 1d`, HTF+width ON, ADX/dwell OFF),
`--tf 1h --fee-bps 4 --oos-split 0.7 --atr-period 14 --trial-count 38 --metrics-only`.

Kill rule: `enrich_fvg_flat_spanb_trend_v0` had to beat champion
`ichi_cloud_bias_tsmom_thin_v0` on fee-aware OOS ATR-normalized
`total_return` for both symbols. It lost both symbols, so the cartridge is
forever killed.

| Date | Cartridge id | Symbols | Split | tf | Flags | HEAD | Host | Metrics | pass_oos_gate | CoS disposition | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-22 | `enrich_fvg_flat_spanb_trend_v0` | PF_XBTUSD + PF_ETHUSD | OOS 70/30 | 1h | `--fee-bps 4 --regime-tf 4h --regime-htf 1d --oos-split 0.7 --atr-period 14 --trial-count 38 --metrics-only` | 9fdf1b1 | dexter paper | OOS ATR total_return: XBT 1.33 vs champion 60.65; ETH 5.80 vs champion 97.61. | false | killed forever | Rank-2 FVG/flat-Span-B overlap loses to `ichi_cloud_bias_tsmom_thin_v0` on both symbols; do not revive. |

Status scope: this bank mutates only `enrich_fvg_flat_spanb_trend_v0` to
`killed`. `ichi_cloud_bias_tsmom_thin_v0` remains `champion_control`; scarred
controls remain unchanged. Intern remains frozen, no control status churn, no
Track A loosening, no live scopes, no ADDR/LTF follow-on, and no killed-id
revival. The rank-2 FVG/flat-Span-B overlap thesis is dead; remaining
enrichment candidates are limited to `daily_dr_side`, `daily_dr_position`, and
cautious `daily_fvg_side`.

## 2026-08-22 failed-auction brain scope

Docs-only scope brief landed at
`docs/briefs/2026-08-22-failed-auction-brain-scope.md`. No dexter run, data
ingest, cartridge status mutation, Intern unlock, live scope, or runtime state
change occurred.

## 2026-08-22 failed-auction data audit park

Docs-only follow-up banks the dexter data audit evidence path
`/var/aura/evidence/audits/failed-auction-data-20260822.json`. Falsifier #1
failed because Kraken-native history lacks the required multi-month
aggressor-signed trades, OI history, liquidation series, and VP stores.

CoS disposition: **PARK** the failed-auction brain on Kraken-native history. Do
not fake absorption from OHLCV. External trade lane or forward-only collection
requires explicit Slim lock and is not started here. No cartridge code, status
mutation, Intern unlock, live scope, or runtime state change occurred.
