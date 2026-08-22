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
