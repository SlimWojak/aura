# Aura dispatch guide

CoS is Grok Bot. Dispatch is about choosing the smallest safe seat for a job
while preserving the paper fence and dexter data gravity.

## Dispatch rules

1. Confirm the task is paper-only and inside `SlimWojak/aura`.
2. Check whether it touches runtime state, repo state, or reasoning only.
3. Send the task to the matching seat below.
4. Require an artifact: PR, memo, JSONL/evidence path, or status note.
5. Do not autopromote. Successful paper work creates review material, not live
   permission.

## Routing table

| Work type | Seat | Boundary |
|---|---|---|
| Repo docs, schemas, templates, tests, stubs, PR cleanup | Cursor cloud agent | Repo-local only; no secrets; no constellation imports/submodules |
| Runtime status, paper runner inspection, risk daemon, scribe, kill drills | SSH to dexter | `/var/aura` is source of truth; futures paper is CLI-only here |
| Market/spot paper MCP checks | Dexter or supervised CoS console | `kraken mcp -s market,paper` only |
| Deep single-shot review, design critique, postmortem draft | Local Claude/Codex/Kimi on MacBook | Paper profile only; no unsupervised runtime authority |
| Backtest or evidence batch work | Dexter worker or disposable cloud PR worker | Runtime/data-heavy work stays on dexter; repo-only artifacts can use cloud |
| Live scopes, live keys, capital promotion, withdraw/funding/earn/subaccount | Nobody | Reject and escalate to Slim |

## Cursor cloud agents

Use when the deliverable should be reviewable in GitHub:

- Operating docs and runbooks
- Risk policy text, schemas, templates, and evidence format changes
- Thin stubs for future runtime components
- Tests for repo-local code when code exists
- PR hygiene and review response work

Cloud agents must not:

- Hold Kraken credentials or secrets.
- Add `trade`, `futures`, `funding`, `earn`, `subaccount`, `all`, or
  `--allow-dangerous`.
- Vendor, import, submodule, or write constellation.
- Treat cloud storage as the paper state of record.

## Dexter runtime work

Use dexter for anything that depends on durable paper runtime state:

- `/var/aura/{market,paper,evidence,logs,scratch,secrets}`
- Kraken futures paper CLI commands
- Future paper runner, risk daemon, and scribe
- Kill-switch drills and heartbeat checks
- Data-heavy backtests after the fence is in place

Read-only safe smoke commands should be wrapped or documented before use. The
starter helper is `scripts/dexter_smoke.sh`.

Any human-triggered futures-paper order must call `runtime.risk.admit()` before
invoking `kraken futures paper ...`. Rejects still append decision JSONL with no
venue call; allowed orders append JSONL with the futures-paper response after
the CLI returns.

## Local Claude/Codex/Kimi delegates

Use local delegates for bounded paper-only thinking:

- Adversarial review of a trial memo
- One-shot design critique
- Search/synthesis over exported paper artifacts
- Refactor sketch before a cloud-agent PR

They must remain delegates, not standing operators. They have no live authority,
no unsupervised paper authority, and no access to constellation write paths.

## Stop conditions

Pause dispatch and escalate to Slim if any task asks for:

- Live Kraken scopes or live credentials
- Withdrawal, funding, earn, subaccount, or transfer capability
- Autopromotion from paper to live
- Constellation code copying, imports, submodules, or write paths
- Paper runtime outside dexter without an explicit CoS decision
- Untraced order state or missing risk admission
