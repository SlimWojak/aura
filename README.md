# aura

Standalone **agent-native trading experiment** — disposable, isolated from constellation / ATOM.

**CoS:** Grok Bot (Chief of Staff) · **Always-on:** dexter DGX Spark · **Venue (paper):** Kraken `market,paper,futures-paper` · **Hetzner:** backup only

## Status
Phase 1 design. Pre-strategy-code. No live trading. Human (Slim) retains capital / risk / go-no-go authority.

## Docs
- [Phase 0 memo](docs/phase0-memo.md) — framing (eval loop + isolation first)
- [Phase 1 runbook](docs/phase1-runbook.md) — repo layout, fence, Kraken scopes, risk, templates, dexter bring-up, kill drills

## Hard fence
No constellation write paths, no clinical LaunchAgents, no RIVER writes, no live Kraken scopes until a separate go. See [ISOLATION.md](ISOLATION.md).
