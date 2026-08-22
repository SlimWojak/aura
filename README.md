# aura

Standalone **agent-native trading experiment** — disposable, isolated from constellation / ATOM.

**CoS:** Grok Bot (Chief of Staff) · **Always-on:** dexter DGX Spark · **Venue (paper):** Kraken spot MCP `market,paper`; futures paper CLI on dexter · **Hetzner:** backup only

## Status
Phase 1 design. Pre-strategy-code. No live trading. Human (Slim) retains capital / risk / go-no-go authority.

## Docs
- [Phase 0 memo](docs/phase0-memo.md) — framing (eval loop + isolation first)
- [Phase 1 runbook](docs/phase1-runbook.md) — repo layout, fence, Kraken scopes, risk, templates, dexter bring-up, kill drills
- [Agent operating manual](AGENTS.md) — standing seats, worker boundaries, host boundaries, paper-only rules
- [Dispatch guide](docs/DISPATCH.md) — how CoS routes repo, runtime, and delegate work
- [Runtime skeleton](runtime/README.md) — reserved paper runner / risk daemon / scribe stubs

## Hard fence
No constellation write paths, no clinical LaunchAgents, no RIVER writes, no live Kraken scopes until a separate go. See [ISOLATION.md](ISOLATION.md).

## How agents work here

Grok Bot is CoS. Cursor cloud agents handle repo PRs and reviewable artifacts.
Runtime and paper state live on dexter under `/var/aura`; Kraken futures paper
is CLI-only there. Local Claude/Codex/Kimi delegates are paper-only deep
single-shot seats, not live operators.

Start with [AGENTS.md](AGENTS.md), [docs/DISPATCH.md](docs/DISPATCH.md),
[RISK_POLICY.md](RISK_POLICY.md), and [ops/kraken_scopes.md](ops/kraken_scopes.md)
before dispatching any agent work.

## Build plan
- [Lean build plan](docs/BUILD_PLAN.md)
