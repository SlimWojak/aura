# Research cartridge queue

This folder is the low-ceremony inbox for Research Intern drafts.

## Intern drop rules

- Add one draft per file.
- Prefer the filename pattern `<short_id>.yaml`.
- Start with `status: draft` unless CoS has already accepted the idea for eval.
- Use the field contract in [`../cartridges/SCHEMA.md`](../cartridges/SCHEMA.md).
- Keep theses paper-only and Ichimoku-first.
- Include sources as URLs or repo-local docs so CoS can audit provenance.

## CoS promotion

CoS promotes a draft by:

1. checking it stays inside the Aura paper fence;
2. normalizing rule vocabulary and kill criteria;
3. moving it to [`../cartridges/`](../cartridges/);
4. setting `status: queued`;
5. running or scheduling a paper backtest/eval;
6. recording the result in the ledger as `tested`, then `killed` or `kept`.

Queue files are not runner inputs. A cartridge in this inbox does not authorize
orders, live scopes, capital, or runtime promotion.
