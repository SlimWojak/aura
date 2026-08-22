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
   - Supported cartridges run through the cartridge eval command:
     ```bash
     python -m runtime.tools.eval_run cartridge --id ichi_v0_baseline --symbol PF_XBTUSD --tf 1h --metrics-only
     python -m runtime.tools.eval_run cartridge --id ichi_adx_regime_v0 --symbol PF_XBTUSD --tf 1h --metrics-only
     python -m runtime.tools.eval_run cartridge --id ichi_params_20_60_v0 --symbol PF_XBTUSD --tf 1h --metrics-only
     python -m runtime.tools.eval_run cartridge --id ichi_chikou_open_space_v0 --symbol PF_XBTUSD --tf 1h --metrics-only
     ```
   - Current runnable cartridge features are baseline Ichimoku v0, alternate
     Ichimoku parameters, strict Chikou open-space confirmation, and ADX entry
     gating. `ichi_tk_cloud_v0` remains a phase-2 seed until eval distinguishes
     TK cross events from the current baseline TK state.
5. **Ledger kill/keep**
   - Results are recorded in the eval/trial ledger with the cartridge id,
     baseline reference, and a short kill/keep rationale.
   - Status changes to `tested`, then `killed` or `kept`.

## Boundaries

- Cartridges describe paper research only.
- They never authorize orders, capital, live scopes, or runner promotion.
- Runtime state belongs on dexter under `/var/aura`; this repository keeps
  reviewable docs, schemas, seeds, and thin loader code.
