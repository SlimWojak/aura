# Phase 0 Research Memo — Standalone Agent-Native Trading Experiment

**Author:** Chief of Staff (Grok Bot)  
**Date:** 2026-08-22 (SGT)  
**Status:** Research only — no production code, zero constellation writes  
**Audience:** Slim — review before any further commitment

---

## 1. Sharpened thesis (challenge to the brief)

The brief proposes: *while ATOM/ICT is hand-tuned, build a parallel system with simpler parametric perception in an agent-optimized environment, and road-test Grok Bot orchestration.*

**Reframe:** For a disposable dual-goal experiment, the highest-leverage axis is **not** “simpler perception.” It is:

1. **Closed-loop evaluation velocity** under agent-native tools (trace → memo → promote/kill)
2. **Hard isolation** from constellation’s clinical surface
3. **Parametric / structural signal families** — only after (1) and (2) work

Why: parametric knobs are cheap to sweep; stable out-of-sample edge is not. Agents overfit as eagerly as humans. Constellation already proves you can build a serious lab OS — the expensive part there is the *brain* (ATOM/ICT + visual ratification). This experiment should steal the lab OS, replace the brain, and make the CoS loop the primary deliverable of Phase paper.

If we only chase a new signal family on a half-agent stack, we neither road-test Grok Bot nor escape chart culture.

**What stays true from the brief:** isolation, research-before-code, human capital authority, disposability.

---

## 2. What to inherit vs orphan from constellation

### Inherit (lab OS)
- Law / Science split — experiment plane cannot write canon or capital
- Paper-first / paper-as-learning-instrument (INV-PAPER-AMNESTY spirit)
- RIVER *shape*: immutable daily parquet + DuckDB views + bitemporal / bar_hash discipline
- Evidence harness → banked ledger (pre-register → run → bank nulls/graves)
- Cartridge *mechanism* (params as data, fail-closed loader) — rewrite vocab for math knobs
- Provenance that can be replayed; no autopromote; arithmetic gates for agents
- BUILD / ADAPT / RENT posture

### Orphan (wrong brain for this experiment)
- Entire ATOM / ICT visual primitives, projector, Olya visual ratification path
- Clinical LaunchAgents (river pairs, ib-gateway, paper-submit, coo-loop, …)
- Galileo ICT recipe / lane DSL that compiles against ATOM
- Live IB / LIVE promotion ceremony
- Full constellation doctrine ocean as day-one charter

**Stance in one line:** *Inherit the lab OS. Replace the brain. Stay off LaunchAgents and clinical write paths. Treat Galileo as a sibling warning label, not a template to clone.*

**Data:** If we ever run an FX control track, RIVER read-only (or sha256-manifested slice) is fine. Primary shortlist below leaves FX — so own a separate artifact/data root. Never write `~/river-data`, never share IB clientIds, never bank into Olya’s curator drawers.

---

## 3. Environment philosophy

| Approach | Agent leverage (near-term) | CoS road-test | Verdict |
|---|---|---|---|
| Lean purpose-built (own backtest + paper broker) | Poor — weeks before honest paper week | Delayed | Defer until hybrid needs fill fidelity |
| Rent platform-as-brain (QuantConnect/Mia, TV GUI) | Fast commodity | **Fails** — tests their orchestrator | Avoid as standing brain |
| **Hybrid** — rent agent-native I/O; own eval/risk/isolation | **Best** | **Best** | **Choose** |

Wild patterns that already encode pieces: Kraken CLI+MCP (paper→live, dead-man), Jesse MCP (mandatory reports), Alpaca MCP, Sentient Trader (audit on paper).

---

## 4. Domain shortlist (logics × markets × venues)

Prefer fully parametric families: z-score / Kalman, funding bands, simple breakout rule packs. Defer market-making and TradingView→MT5.

| ID | Combo | Role |
|---|---|---|
| **S1** | **Kraken futures-paper + parametric stats / funding bands** | **Primary** — max agent ownership (official Cursor MCP/CLI, paper-by-default) |
| **S2** | Hyperliquid testnet + funding/basis + on-chain flow | **Parallel structural track** — only after S1 loop works; DIY agent surface |
| **S3** | IBKR FX paper + RIVER + mean-rev/breakout | **Control only** — continuity with constellation; not the learning-max path |

**Hyperliquid is not the default** for the Grok orchestration road-test. Strong API and unique public state; weak first-party agent UX vs Kraken/Bybit. Use as structural thesis track, not as CoS proving ground. Travel/jurisdiction: prefer paper/testnet until itinerary is checked.

Bybit testnet+MCP is honorable mention if Kraken geo/product coverage fails.

---

## 5. Recommended operating model (Grok-centered)

### Placement
- **CoS (me):** stay on MacBook — interactive orchestration, memos, kill/promote, human interface
- **Always-on paper runner + risk daemon:** **one** of sandboxed Mac Mini **or** 24/7 VPS (don’t split brains). Travel → VPS wins
- **Heavy disposable jobs:** Cursor cloud agents (repo PRs) or SSH to M3/M4 — **read-only / separate paths only**; never clinical LaunchAgents
- Do **not** put live/paper execution on a sleeping laptop

### Topology
**Standing (small):** CoS · Risk/Ops (script-heavy, LLM-light) · Eval/Scribe  
**Disposable default:** thesis scout, backtest runner, postmortem writer, connector spike  
**Delegates (Claude / Codex / Kimi):** paper-scoped seats only, never unsupervised live  
Avoid standing “trader/sentiment” LLM theater until eval loop exists

### Tools to request (when you greenlight Phase 1)
| Priority | What |
|---|---|
| P0 | Kraken connector — `market,account,paper` only |
| P0 | Separate git repo/org for the experiment |
| P1 | Optional Alpaca paper if equities enter scope |
| P1 | Thin reviewed Hyperliquid wrapper + API wallet (testnet) — later |
| P2 | Email for alerts/digests only |
| Avoid early | Full live trade/funding/withdraw tools; main HL key on agent host; QuantConnect-as-brain; TV GUI path |

### Evidence artifacts (human stays high-agency)
1. Per-decision JSONL (thesis, tools, fills, risk gates)  
2. Daily one-pager · Weekly promote/iterate/kill memo  
3. Tiny dashboard (equity, open risk, last kill-switch drill, MCP health)  
4. Soft kill (pause entries) / hard kill (cancel-all + disable live MCP) / dead-man (cancel-after)

---

## 6. Success metrics, kill criteria, phases

### Success (pre-declare; CoS-weighted in Phase paper)
- Median thesis → paper order under agreed hours
- ≥90% decisions fully traced
- Cold kill-switch drill succeeds
- Human weekly review &lt; ~30 min
- Trading metrics secondary until paper honesty is proven

### Kill (any one)
- Untraced or unauditable live-capable actions
- Risk-gate bypass or secret leakage across constellation fence
- Look-ahead / broken-fill paper results after audit
- CoS overhead turns you into ticket clerk
- No hypothesis survives two weekly kill reviews
- Soft capital or emotional stop

### Phased plan
| Phase | Goal | Exit |
|---|---|---|
| **0 — this memo** | Framing | You pick hybrid + shortlist + open Qs |
| **1 — design** | Repo layout, MCP scopes, risk policy, memo templates, compute choice | Written runbook + dry kill-switch — **still pre-strategy-code** |
| **Paper** | Kraken paper only; CoS + disposable workers | 2–4 weeks continuous traces + 2 weekly memos |
| **Tiny capital** | Least-privilege live; dead-man on | Survive N days with no policy breach, then re-decide |

---

## 7. Recommendations (conviction)

1. **Run this experiment** — but as a **CoS + evaluation OS road-test**, not as “find ICT-lite alpha first.”
2. **Hybrid stack**, not greenfield Nautilus/Freqtrade and not platform-as-brain.
3. **Primary venue: Kraken futures-paper (S1).** HL testnet (S2) only as a later structural parallel. IBKR FX (S3) optional control — default **cut** to avoid constellation gravity.
4. **Placement:** CoS on MacBook; always-on on **VPS or Mini** (you pick). M3 is a worker hop, not the clinical home of this experiment.
5. **Inherit lab OS patterns; orphan ATOM/ICT/LaunchAgents.** Separate git, data root, credentials, MCP profiles.
6. **Do not install trading connectors or mint venue keys until Phase 1 runbook is agreed.**

---

## 8. Open questions (need you)

1. Confirm **CoS road-test ≥ trading PnL** as Phase-paper priority? (Recommended: yes.)
2. **Always-on host:** sandboxed Mac Mini vs VPS?
3. **FX stay or leave?** Recommend leave (cut S3) unless you want an explicit control.
4. **HL timing:** defer until S1 loop works, or start thin testnet spike in Phase 1 design?
5. **Jurisdiction / travel:** which countries are on the itinerary before any live keys?
6. **Delegate budget:** which of Claude Code / Codex / Kimi are approved as paper-only seats, and spend ceiling?
7. **Perception constraint:** must every signal stay human-auditable on OHLC, or may the math layer be non-chart-eyeable?
8. **Promotion story:** forever parallel and disposable, or eventual “alternate brain” attach path into constellation Science (never Law)?
9. **Evidence bank home:** new repo ledger vs quarantined curator namespace? (Recommend new repo.)
10. **Email / wallet:** alerts-only email OK? Wallet = read-only watch vs signing (recommend read-only / API wallet only)?

---

## 9. Exact next step (still pre-code)

**Phase 1 Design Spike (no strategy implementation):**  
Produce a short runbook covering: repo name/layout, isolation fence checklist, Kraken MCP scope (`paper` only), risk policy draft, memo/JSONL templates, compute choice (Mini vs VPS), and a dry kill-switch drill plan. After you answer the open questions above (even partially), I draft that runbook and we review before any connector install or capital path.

---

*Sources: read-only M3 doctrine/river/research/curator skim; web venue/MCP survey (Kraken, HL, Bybit, IBKR, MT5, TV); agent-stack environment survey. No writes to constellation, no `.env` reads, no clones.*
