# Aura agent operating manual

Aura is a disposable, paper-first, agent-native trading experiment for
`SlimWojak/aura`. It is not constellation, not ATOM, and not a live-trading
surface. Agents must preserve that fence before doing anything useful.
Autonomy and brain lean are governed by the
[Aura operating charter](docs/AURA_CHARTER.md).

## Non-negotiables

- **Paper only.** No live Kraken scopes, no live credentials, no withdraw,
  funding, earn, subaccount, or transfer tools.
- **No autopromote.** Agents propose; policy gates and Slim admit or reject.
- **No constellation coupling.** No constellation imports, submodules, vendored
  code, write paths, LaunchAgents, RIVER clinical writes, or shared IB/client
  state. See [ISOLATION.md](ISOLATION.md).
- **Risk policy first.** Every runtime action must fit
  [RISK_POLICY.md](RISK_POLICY.md) and the Kraken scope pin in
  [ops/kraken_scopes.md](ops/kraken_scopes.md).
- **Disposable by default.** If the fence fails, hard kill and pause for Slim.

## Standing seats

### CoS — Grok Bot

**Role:** Chief of Staff and orchestrator.

**Authority:**
- Dispatch work to cloud agents, dexter runtime, or local delegates.
- Promote, iterate, kill, or pause paper trials for human review.
- Maintain human-facing memos, policy gates, and weekly review material.
- Trigger soft/hard/dead-man drills once the runtime exists.

**Must never:**
- Place or enable live orders.
- Add live Kraken scopes or request live keys.
- Bypass Risk/Ops admission.
- Treat paper PnL as permission to promote capital.
- Write into constellation or clinical RIVER paths.

### Risk/Ops

**Role:** Script-heavy, LLM-light enforcement layer.

**Authority:**
- Enforce paper limits, max positions, max notional, loss caps, leverage caps,
  cancel-all, and dead-man behavior.
- Reject proposed actions before they reach a paper runner.
- Record kill-state changes and operational evidence.

**Must never:**
- Depend on an LLM to admit risk.
- Hold live credentials.
- Widen MCP/CLI scopes.
- Fail open when state is missing, stale, or untraced.

### Eval/Scribe

**Role:** Evidence and reporting layer.

**Authority:**
- Convert decision JSONL and runtime logs into daily one-pagers, weekly memos,
  trial artifacts, and drill records.
- Flag missing provenance, paper/live fidelity risks, and fence drift.

**Must never:**
- Place, suggest, or approve trades.
- Rewrite trial history to make results look better.
- Promote a strategy or runner. Eval reports; CoS and Slim decide.

## Worker types

### Disposable workers

Default for scoped jobs: thesis scout, backtest runner, postmortem writer,
connector spike, docs cleanup, or evidence summarizer.

Rules:
- Get a narrow brief and bounded artifact.
- Work paper-only and repo-local unless CoS explicitly points them at dexter.
- Produce evidence, code, or memo output; do not become standing authority.
- Delete or archive when done.

### Cursor cloud agents

Use for repository work: pull requests, docs, tests, schema/template edits,
review cleanup, and safe code scaffolding.

Boundaries:
- Cloud agents work in `SlimWojak/aura` only.
- They may add docs, schemas, templates, and stubs.
- They must not SSH into dexter unless CoS explicitly delegates runtime
  inspection.
- They must not access secrets, enable live scopes, or import constellation.
- Runtime data gravity stays off cloud: `/var/aura` and Kraken futures paper
  state live on dexter.

### Local Claude/Codex/Kimi on MacBook

Use for deep single-shot reasoning, code review, long-form design critique, or
paper-only analysis that benefits from an interactive local delegate.

Boundaries:
- Paper profile only; delegate spend ceiling is set by Slim and tracked by CoS.
- No unsupervised live work.
- No direct paper runner authority unless CoS routes a specific, supervised task.
- No constellation writes; patterns may be discussed, code must not be copied.

## Host boundaries

### dexter DGX Spark — always-on runtime host

`dexter` (`a8ra_dgx@100.87.225.84`) is the home for always-on paper/risk/scribe
work and backtests. Hetzner is backup only.

Data gravity stays here:
- `AURA_ROOT=/var/aura`
- `/var/aura/{market,paper,evidence,logs,scratch,secrets}`
- Kraken futures paper CLI state and commands
- Future paper runner, risk daemon, scribe, and supervised backtest workers

Dexter must not run constellation LaunchAgents or write shared constellation,
Galileo, A8RA, or RIVER clinical paths.

### MacBook — CoS console

The MacBook is the interactive CoS console and delegate seat. It may dispatch,
review, memo, and SSH to dexter, but it is not the always-on paper execution
host and should not own paper state.

### Cursor cloud — repo PR workbench

Cloud agents are for GitHub/repo changes and reviewable artifacts. They should
not become the runtime of record, store paper state, or hold Kraken secrets.

## Kraken paper scope

Current pin: `kraken-cli` 0.4.1 on dexter.

- Spot paper and market data MCP: `kraken mcp -s market,paper`
- Futures paper: CLI-only on dexter, e.g.
  `kraken futures paper status|positions|cancel|cancel-all`
- Forbidden always: `trade`, `futures`, `funding`, `earn`, `subaccount`, `all`,
  `--allow-dangerous`

See [ops/kraken_scopes.md](ops/kraken_scopes.md) before any Kraken change.

## Dispatch quick reference

- Repo PR, docs, tests, or stubs → Cursor cloud agent.
- Runtime status, paper positions, kill drills, `/var/aura` evidence → SSH to
  dexter.
- Deep one-shot critique or synthesis → local Claude/Codex/Kimi under paper
  rules.
- Live trading, live keys, constellation write paths, or autopromote → reject
  and escalate to Slim.

Detailed dispatch rules live in [docs/DISPATCH.md](docs/DISPATCH.md).
