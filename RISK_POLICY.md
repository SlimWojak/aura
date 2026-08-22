# Risk policy draft (paper phase)

Mode: **paper only**. Live MCP absent.

| Rule | Default | Notes |
|---|---|---|
| Max notional / order | TBD Slim | Daemon rejects oversize |
| Max open positions | TBD (start 1–3) | |
| Max daily loss (paper) | TBD % | Soft kill |
| Max weekly loss | TBD | Hard kill |
| Leverage cap | Venue paper max or lower | Prefer lower |
| Dead-man N | TBD (5–15 min) | Risk daemon owns heartbeat |
| Withdraw/funding tools | Forbidden | |
| Autopromote to live | Forbidden | |
| Untraced order | Hard kill | |

LLM proposes; risk daemon admits/rejects. Delegate spend ceiling: TBD Slim.
