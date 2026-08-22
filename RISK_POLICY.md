# Risk policy (paper phase) — locked defaults 2026-08-22

Mode: **paper only**. Live MCP absent. Starting paper equity reference: **USD 10,000** futures-paper collateral on dexter.

| Rule | Value | Enforcement |
|---|---|---|
| Max notional per order | **USD 500** (5% of paper equity) | Reject oversize |
| Max open positions | **2** | Reject new opens above cap |
| Max daily loss | **USD 200** (2%) | Soft kill |
| Max weekly loss | **USD 500** (5%) | Hard kill |
| Leverage cap | **2×** | Prefer set-leverage ≤ 2 |
| Dead-man N | **10 minutes** | Risk daemon heartbeat (to be wired) |
| Withdraw/funding tools | Forbidden | |
| Autopromote to live | Forbidden | |
| Untraced order | Hard kill | |
| Delegate spend ceiling | **USD 50 / week** (Claude/Codex/Kimi) | CoS tracks |

## Kill hierarchy
1. Soft — pause new entries; alert
2. Hard — cancel-all paper; disable order paths; alert
3. Dead-man — no heartbeat for N → flatten/cancel-all

LLM proposes; policy admits/rejects. Slim may revise ceilings anytime.
