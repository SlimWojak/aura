# Isolation fence checklist

## Git
- [ ] Work only in `SlimWojak/aura` (this repo)
- [ ] No submodule / vendor tracking live constellation
- [ ] Branch protection on `main` once paper starts

## Data (dexter)
- [ ] Root: `/var/aura/{market,paper,evidence,logs,scratch,secrets}`
- [ ] Never `RIVER_ROOT=~/river-data` (clinical)
- [ ] Never write constellation `.staging`, curator `factory/`, atom_vault
- [ ] No shared paths with `~/galileo*`, `~/a8ra` on dexter

## Credentials / MCP
- [ ] Vault namespace `aura/`
- [ ] Kraken MCP: `-s market,paper,futures-paper` only
- [ ] No `trade` / `futures` / `funding` / `earn` / `subaccount` / `all`
- [ ] No withdraw tools; no main HL key on agent hosts
- [ ] Delegates (Claude/Codex/Kimi) paper profile only

## Process
- [ ] No constellation LaunchAgents on dexter
- [ ] No IB Gateway / clientId sharing
- [ ] CoS laptop is not the paper execution host
- [ ] playground-dgx left to Galileo; M4 deferred until online

**Fence breach = hard kill + pause pending Slim review.**
