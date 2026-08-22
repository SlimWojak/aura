# Aura operating charter

## Thesis

Aura is a low-ceremony, high-autonomy, disposable-capital paper experiment.
The point is to learn how Grok Bot as Chief of Staff can run agent-native
trading build/ops with honest traces, risk gates, and short review loops.
In paper phase, eval honesty beats PnL.

## Brain lean

The v0 brain is **Ichimoku**: mathematical, explicit, and testable on OHLCV.
It is **not** ICT, ATOM, chart-culture lore, or visual ratification.

Domain: BTC, ETH, and other crypto majors through Kraken futures paper first.
A parallel Hyperliquid structural track can come later, but it is not blocking.

## Fence

Aura stays forever parallel and disposable by default.

Forbidden:
- Constellation imports, submodules, vendored code, or write paths.
- Clinical RIVER writes or shared `~/river-data` state.
- Clinical LaunchAgents.
- Live Kraken scopes: `trade`, live `futures`, `funding`, `all`, or
  `--allow-dangerous`.
- Live capital or irreversible actions outside the paper fence.

Fence breach means hard kill and human review before resuming.

## Roles

- **Grok Bot Chief of Staff:** primary high-autonomy orchestrator.
- **Research Intern:** disposable thesis scout that drafts paper-only cartridges
  in [`research/`](../research/README.md); CoS decides backtest, kill, or keep.
- **Cursor cloud agents:** repo pull requests and reviewable artifacts.
- **Claude/Droid on dexter:** runtime-adjacent implementers under briefed
  MISSIONs, paper-only.
- **Slim:** daily check-ins; gates live capital, ceiling raises, and fence
  exceptions.
- **Grok Desktop:** optional chairman/oversight through read repo access.

## Autonomy matrix

CoS may do without asking, inside the paper fence:
- Merge paper PRs after green tests and dexter smoke.
- Write thin cloud/Droid briefs.
- Install tools on dexter or boxed hosts when scopes remain paper-only.
- Run paper drills under [RISK_POLICY.md](../RISK_POLICY.md) ceilings.
- Maintain digest routines, JSONL evidence, and short memos.

CoS must ask Slim before:
- Any live scope or credential path.
- Any capital above approved ceilings.
- Any fence exception.
- Anything irreversible outside paper.

## Risk ceilings

Risk ceilings live in [RISK_POLICY.md](../RISK_POLICY.md). Do not duplicate
the numbers here. Summary: paper-only mode, small per-order and open-position
limits, daily/weekly loss kills, leverage cap, dead-man heartbeat, forbidden
funding/withdrawal tools, and delegate spend ceilings.

## Promotion

Paper-to-live is always human-gated. There is no autopromote from paper PnL,
green tests, weekly memos, or agent confidence.

## Ceremony

Prefer thin JSONL evidence and short memos over heavy process. Claude jousts
only at milestones or when CoS needs adversarial review.
