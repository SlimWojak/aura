# Failed-auction brain scope — 2026-08-22

Paper-only. New brain candidate for Aura after Ichimoku entry mill exhaustion. Not
a live scope. Intern remains frozen until data + IC exist.

## Claim

Trade crypto perps only when HTF auction is unbalanced, price is outside value in
discount/premium, aggressive effort fails to progress (absorption/trap), then
dominance flips. Not an Ichimoku equilibrium map.

## Refuse to fake from the NQ recipe

- GEX / call-put walls / gamma flip (equity options dealer mechanics)
- Footprint ">400% imbalance" without true trade prints
- NQ NY-open session cosplay on 24/7 crypto
- Multi-venue volume profile while evaluating on Kraken alone
- Fib golden pocket as a standalone brain
- Prop-firm 1.5–2R targets as edge proof
- Absorption proxies built only from 1h OHLC wicks

## Data needs

### Must-have before any cartridge

- Historical aggressor-signed trades (or equivalent) for PF_XBTUSD and PF_ETHUSD
  → CVD/delta and effort-vs-result
- Single-venue volume profile (VA/POC/VAH/VAL) from those trades or tick bars
- Session/volume-regime tags (US/EU/Asia participation), not clock cargo-cult

### Should-have

- Open interest + funding (funding already partially present on dexter)
- Liquidation markers as forced-participation events

### Nice/later

- L2 snapshots for book imbalance
- External liquidation feeds if Kraken history is thin

### Already have (insufficient alone)

- 1h/4h OHLCV, funding store, IC/eval harness
- Thin TREND spine may be an optional side prior later — not this brain

## Falsifiers (pre-registered)

1. If ≥6–12 months usable trades cannot be backfilled for both symbols → park
   the brain; do not fake with OHLCV.
2. Location-only (value area + outside-value discount/premium; fib optional)
   must be IC/bake-off tested and can die before flow is added.
3. Absorption proxy must beat location-only on fee-aware OOS ATR for both symbols
   or die.
4. Full stack must beat champion control `ichi_cloud_bias_tsmom_thin_v0` on both
   symbols or die.
5. Hard aside when LTF participation is below a pre-registered volume quantile
   (crypto analog of NQ <20k/5m). If the filter never binds, session thesis is
   fake.

## Audit / Falsifier #1

Evidence: `/var/aura/evidence/audits/failed-auction-data-20260822.json`

- Dexter store: OHLCV 1h/4h 2023-04-11→2026-08-22; funding
  2025-08-20→now; NO trades/OI history/liq/VP stores.
- Kraken Futures: `/history` ≈100 recent trades (~7d docs); older `lastTime`
  empty; OI current-only on tickers; no public historical liquidation series
  found.

Verdict: Falsifier #1 FAIL → PARK failed-auction brain on Kraken-native history.
Do not fake absorption from OHLCV. External trade lane or forward-only collect
require explicit Slim lock (not started).

## Build order

1. Data audit on dexter/Kraken: trades, OI, liquidations availability + history
   depth
2. Store schema under /var/aura
3. VP + regime features + IC screen
4. Location-only cartridge one-shot
5. Absorption cartridge one-shot
6. Second-chance pullback only if prior steps survive

Ichimoku entry mill stays parked (controls only). No constellation clinical
import. No ADDR/LTF dealing-range wounds.

## Fence

Paper Kraken futures only. No live. No Intern unlock until data+IC. No revive of
killed ids.
