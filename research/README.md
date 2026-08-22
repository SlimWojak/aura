# Aura research cartridges

Aura research starts as paper-only theses and only becomes runtime behavior
after CoS backtests and records a kill/keep decision. Cartridges are the small,
machine-readable handoff between the Research Intern and CoS.

## Workflow

1. **Thesis**
   - Research Intern writes one narrow idea: what market condition the rule is
     trying to avoid or capture.
   - Keep the scope Ichimoku-first and Kraken futures paper-first.
   - No live trading, live Kraken scopes, Nansen/Binance additions, or
     constellation coupling.
2. **Draft cartridge**
   - Drafts can be dropped in [`queue/`](queue/) while they are incomplete.
   - Use the schema in [`cartridges/SCHEMA.md`](cartridges/SCHEMA.md).
   - Defaults are `symbol: PF_XBTUSD`, `tf: 1h`, and
     `baseline_ref: ichimoku_v0`.
3. **CoS promotion**
   - CoS reviews the draft for fence safety, normalized vocabulary, and testable
     kill criteria.
   - Accepted drafts move to [`cartridges/`](cartridges/) with status `queued`.
4. **Paper backtest**
   - CoS runs the existing paper eval path, starting with
     `python -m runtime.tools.eval_run backtest --symbol PF_XBTUSD --tf 1h`.
   - Cartridge-specific regime gates or rule variants may require follow-up
     eval wiring; this queue does not imply runtime admission.
5. **Ledger kill/keep**
   - Results are recorded in the eval/trial ledger with the cartridge id,
     baseline reference, and a short kill/keep rationale.
   - Status changes to `tested`, then `killed` or `kept`.

## Boundaries

- Cartridges describe paper research only.
- They never authorize orders, capital, live scopes, or runner promotion.
- Runtime state belongs on dexter under `/var/aura`; this repository keeps
  reviewable docs, schemas, seeds, and thin loader code.
