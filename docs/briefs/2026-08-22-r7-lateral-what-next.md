# Aura R7 lateral review brief — banked state & what next

Date: 2026-08-22

Repo tip context: main after PR #35 merge `e81574d` (honesty bank). Prior R7 bank PR #34 `5005ba3`.

Host/evidence: dexter; paper Kraken futures only.

## Intent (Phase 0)

Disposable standalone paper experiment (isolated from constellation). Closed-loop eval velocity + hard isolation. Ichimoku as v0 mathematical brain. CoS orchestrates; live always human-gated. CoS/eval priority over PnL in paper phase.

## Seats / loop

Intern proposes cartridges → CoS bake-off on dexter → Integrity gates merges → Curator statuses → Scribe LEDGER/memos. Never revive killed ids.

## Production spine (locked)

Thin Phase-2 regime: HTF veto ON, kumo width ATR ON, ADX/DI OFF, dwell OFF. Ablation evidence: HTF KEEP_IN_SPINE; ADX+dwell DROP_CANDIDATE; width INCONCLUSIVE; AB-0 beat AB-FULL (gate was overbuilt).

## What was tested (families)

Entries: TK-strong (+refinements), kijun/tenkan bounce, TK cross, kumo break (full+thin), params 20/60 + 10/30, ETH-primary/BTC-confirm, long_only/n8, always_on TSMOM thin, cloud_bias TSMOM thin.

Exits: timestop, regime_exit, kijun_trail, ATR stop, chandelier — all killed vs bias_flip parent.

Honesty: Track A ATR-norm + DSR/PBO/CSCV.

## Controls after status hygiene

1. `ichi_params_20_60_trend_v0` — `scarred_control`; Track A provisional-fail (N_honest=34). BTC OOS ATR can beat baseline; ETH fails; DSR ~0.15; PBO fails strict <0.10.
2. `ichi_always_on_tsmom_thin_v0` — `scarred_control`; R7 bake-off provisional keep then honesty provisional-fail (N=37). BTC beats thin baseline OOS ATR; ETH loses; DSR tiny (~0.02).
3. `ichi_cloud_bias_tsmom_thin_v0` — `champion_control`; strongest residual ATR (beats thin baseline BTC+ETH OOS ATR; BTC DSR ~0.34, ETH DSR ~0.73) but still Track A provisional-fail; ETH PBO 0.34 / Mixed 0.13 fail.

Sequence is locked as paper-only control hygiene: no runner promotion, no live
scope, no revive, and Intern R8 remains frozen.

Killed forever (non-exhaustive but important): TK-strong family, kumo_break (full+thin), most R3–R6 polish, all Track C exits.

Evidence dirs (dexter):

- `/var/aura/evidence/evals/r7-thin-spine-20260822/`
- `/var/aura/evidence/evals/r7-dsr-pbo-20260822/`
- `/var/aura/evidence/evals/track-a-rescore-20260822/`
- `/var/aura/evidence/evals/phase2-ablation-20260822/`
- `/var/aura/evidence/evals/track-c-exit-vocab-20260822/`

## CoS working hypothesis (for reviewers to attack)

Eval loop is healthy; alpha bar is correctly brutal; nothing clears Track A. Blind Intern R8 has low EV. Prefer: (a) lateral review, (b) close width inconclusive + honesty scars (PBO runnable paths << N_honest), (c) only then one endorsed next family — or pause.

## Ask to Fable 5 and Grok Desktop (answer both)

1. Rank next moves: unlock Intern R8 / width ablation / honesty-infra (PBO/trial accounting, data lane) / change brain beyond Ichimoku / pause.
2. What is the single highest-EV next experiment under paper fence?
3. Are the three kept ids worth preserving, forever-killing, or demoting?
4. Is Track A gate (DSR>0.95 ∧ PBO<0.10 ∧ both-symbol ATR beat) calibrated for this sample size, or too strict / too loose?
5. Any missed Ichimoku/regime angle not already scarred?

Reply format requested: half-page max; bullets; explicit recommendation + one falsifier.
