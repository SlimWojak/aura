# Kraken scope (paper only) — dexter pin

## CLI pin
- version: **0.4.1**
- binary: `/home/a8ra_dgx/.cargo/bin/kraken` (`aarch64-unknown-linux-gnu`)
- installed_on: dexter
- date: 2026-08-22
- futures paper account: initialized (USD 10,000 simulated collateral)

## MCP (agent tools)
```text
kraken mcp -s market,paper
# wrapper: ~/aura/ops/kraken-mcp-paper.sh
```

**Important (0.4.1):** there is **no** MCP service named `futures-paper`.
Valid services include: `market`, `account`, `paper`, `workspace`, `feedback`, and live-dangerous: `trade`, `futures`, `funding`, `earn`, `subaccount`, `all`.

Do **not** enable `futures` (that is live futures). Use CLI for futures paper:

```text
kraken futures paper status|buy|sell|cancel|cancel-all|positions|...
```

## Forbid
`trade`, `futures`, `funding`, `earn`, `subaccount`, `all`, `--allow-dangerous`

No API keys required for spot `paper` or CLI `futures paper`.
