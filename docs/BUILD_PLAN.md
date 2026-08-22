# Aura lean build plan

Living plan for CoS (Grok Bot). Paper-first. Disposable. No constellation coupling.
Charter source of truth: [AURA_CHARTER.md](AURA_CHARTER.md).

Last updated: 2026-08-22

## North star (near term)

Prove a **closed paper loop on dexter** that agents can run without Slim staring at charts:

`thesis → risk gate → Kraken futures-paper (CLI) → JSONL evidence → daily/weekly memo`

CoS road-test and eval honesty beat PnL until that loop is boringly reliable.

## Where we are (done)

- [x] Phase 0 framing + Phase 1 runbook
- [x] Repo `SlimWojak/aura` + fence docs + risk ceilings
- [x] Dexter always-on host; Hetzner backup only
- [x] `~/aura` + `/var/aura` on dexter
- [x] Kraken CLI 0.4.1 paper; futures-paper smoke open/flat
- [x] Kraken Cursor connector (paper-only instructions)
- [x] Agent workplace scaffold (AGENTS.md, DISPATCH.md, Cursor fence rule, runtime stubs)
- [x] Aura operating charter: autonomy, brain lean, paper fence, promotion gate
- [x] Kill-drill CLI wiring and one-shot drill smoke; repeat before unsupervised paper

## Delegates on dexter (target)

| Tool | Status | Role |
|---|---|---|
| Droid (Factory) | **Installed** 0.120.1 | On-box implementer near `/var/aura` |
| Claude Code CLI | **Installed** 2.1.239 (auth OK) | Deep implement / review on dexter |
| Codex CLI | Missing | Optional third; install if diversity needed |
| Cursor IDE/CLI | Missing | Skip on dexter; use cloud agents for PRs |
| Kraken CLI | Installed | Spot MCP `market,paper`; futures paper CLI-only |

## Build phases (lean)

### P0 — Agent workplace ops (current)
1. [x] Install **Claude Code CLI** on dexter (2.1.239, logged in).
2. [x] Document Droid + Claude invoke recipes in `ops/delegates.md`.
3. Optional: install Codex on dexter if first Claude+Droid week feels thin.
4. Create standing Grok seats **only when needed**: Risk/Ops, Eval/Scribe (not before runtime stubs run).

### P1 — Thin paper runtime (next)
1. [x] `runtime/risk` stub — admit/reject against RISK_POLICY.md (no LLM in the gate).
2. [x] `runtime/evidence` + smoke stub — runner can gate proposals and append decision JSONL.
3. [x] First `runtime/runner` supervised paper loop — human trigger only; reads futures-paper status/positions, calls `admit()`, writes JSONL, and invokes only `kraken futures paper buy|sell` after allow.
4. `runtime/scribe` — daily one-pager from JSONL (template already exists).
5. No systemd runner yet. Any future user units require a separate explicit design/review; this loop remains human-triggered.
6. [x] Kill-drill CLI wiring for A/B/C: soft, hard cancel/flatten, heartbeat,
   and one-shot dead-man check. No background daemon yet.

Exit: CoS can request a tiny supervised paper action end-to-end with traces; cold kill drill passes.

### P2 — OHLCV spine + Ichimoku v0 (after P1 honest)
1. [x] Market OHLCV spine for Kraken futures-paper majors via public Kraken
   Futures Charts REST; no live scopes, no strategy, no Ichimoku yet.
2. [x] Ichimoku v0 signal brain: standard 9/26/52 + 26 displacement, deterministic
   `long`/`short`/`flat` output, JSONL evidence, optional dry supervised proposal;
   **not** ICT/ATOM and not live trading.
3. Eval harness: pre-register trial → paper run → bank nulls/graves in LEDGER.
4. Weekly kill/promote memo; CoS metrics still primary.

Exit: ≥2 weekly memos with honest traces; no fence breaches.

### P3 — Structural track (later)
1. Hyperliquid testnet **read-only** spike → then structural signals if S1 loop is honest.
2. Still no live capital without Slim go + Singapore eligibility check.

## Explicit non-goals (until Slim says otherwise)

- Live Kraken / live HL
- IBKR FX control track
- Forking constellation / ATOM perception
- Greenfield backtester platform before paper loop works
- Standing LLM "trader personas" without eval loop

## CoS weekly rhythm (once P1 lands)

- Daily: auto one-pager in `/var/aura/evidence` + optional alert email
- Weekly: promote / iterate / kill memo (<30 min Slim review)
- On fence breach: hard kill + pause

## Next concrete actions (ordered)

1. [x] Install Claude CLI on dexter and smoke version from SSH.
2. [x] Add `ops/delegates.md`.
3. [x] Cloud-agent PR: P1 risk-gate stub + JSONL writer (no strategy).
4. [x] First supervised runner loop (still human-triggered).
5. [x] Kill-drill CLI wiring and one-shot drill smoke.
6. [x] Market OHLCV spine.
7. [x] Ichimoku v0 signal/evidence path.
8. Eval harness.
