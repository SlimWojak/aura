# Phase 1 Design Runbook — Agent-Native Trading Experiment

**Status:** Design spike (pre-strategy-code). No connector install, no keys, no capital until human review + greenlight.  
**Date:** 2026-08-22 (SGT)  
**Owner:** Chief of Staff (Grok Bot) · Human authority: Slim (capital, risk ceilings, go/no-go)

**Locked from Phase 0 + host decision:** hybrid stack · Kraken futures-paper primary · HL structural later · IBKR FX cut · CoS interactive · **always-on = dexter DGX Spark** (Hetzner backup only) · paper-only delegates · forever parallel/disposable · CoS/eval > PnL in paper phase.

---

## 0. One-page operating picture

```
[Slim] ← weekly memo / kill flips
   ↑
[Grok Bot CoS — MacBook]  orchestration, promote/kill, human interface
   │
   ├── disposable workers (cloud agents / Kimi / Codex / Claude — paper scopes only)
   │
   └── [Always-on: dexter DGX Spark — Ubuntu 24.04 aarch64]
         ├── paper runner (Kraken futures-paper)
         ├── risk daemon (limits, cancel-all, dead-man)
         ├── eval scribe (JSONL → daily/weekly artifacts)
         └── backtest workers (cgroup-limited concurrency)
         # Hetzner CCX/AX = backup only if home WAN/power fails
```

Constellation / M3 clinical surface: **out of band**. M3 = temporary extreme-sweep hop only, under the same isolation fence.

---

## 1. Repo name / layout

### Proposed names
| Item | Proposal | Notes |
|---|---|---|
| GitHub owner | **`SlimWojak/aura`** (locked) | Org deferred; locked under SlimWojak for Phase 1. Prefer **new org** later if needed (`a8ra-lab` / `riverglass` / similar — you pick) so accidental constellation PRs are harder |
| Repo | **`SlimWojak/aura`** | Locked 2026-08-22. |
| Default branch | `main` | |
| Visibility | Private | |

**Repo locked:** https://github.com/SlimWojak/aura

### Layout (thin — no strategy packages yet)

```
aura/
  README.md                 # purpose, fence, paper-first, how to kill
  CHARTER.md                # Law/Science split for THIS experiment (short)
  ISOLATION.md              # fence checklist (copy of §2)
  RISK_POLICY.md            # copy of §4
  AGENTS.md                 # standing seats + disposable worker rules
  docs/
    phase0-memo.md          # archived
    phase1-runbook.md       # this file
  evidence/
    LEDGER.yaml             # banked trials index
    trials/                 # one dir per pre-registered trial
    memos/                  # daily/weekly human-facing
  schemas/
    decision_event.schema.json
    trial_manifest.schema.json
  templates/
    daily_onepager.md
    weekly_memo.md
    trial_prereg.md
  ops/
    kill_switch.md          # drill + procedures
    vps.md                  # provisioning + concurrency
    kraken_scopes.md        # paper-only allowlist
    hl_spike.md             # optional testnet notes
  runners/                  # Phase paper+ — empty stubs only in Phase 1
  risk/                     # Phase paper+ — policy-as-code later
  .github/
    PULL_REQUEST_TEMPLATE.md
```

**Explicitly absent in Phase 1:** strategy code, live adapters, shared submodules pointing at constellation, any path under `~/constellation` or `~/river-data` as write target.

### Inherit as *patterns* (copy ideas, not live imports)
- Evidence bank + LEDGER (from strategy_curator/factory spirit)
- Trial manifest stamps (pin, range, data-as-of, content hash)
- Paper-first / no autopromote
- Cartridge-as-data (params YAML later) — vocab rewritten for math knobs

---

## 2. Isolation fence checklist

Check before every worker touch and before any VPS bootstrap.

### Git
- [ ] Repo is **not** inside constellation / research / curator / projector trees
- [ ] No git submodule or vendor path that tracks live `~/constellation`
- [ ] Remotes only on the experiment org/repo
- [ ] Branch protection on `main` (PR required once paper starts)

### Data
- [ ] Dedicated data root on VPS, e.g. `/var/aura/` (or `/data/aura/`)
- [ ] Subdirs: `market/`, `paper/`, `evidence/`, `logs/`, `secrets/` (secrets not in git)
- [ ] **Never** set `RIVER_ROOT` to clinical `~/river-data`
- [ ] **Never** write constellation `.staging`, curator `factory/`, or atom_vault
- [ ] If an FX control is ever revived: read-only manifested RIVER *slice* only, sha256 attested

### Credentials / MCP
- [ ] Separate vault namespace / password manager folder: `aura/`
- [ ] Cursor MCP profile **paper** ≠ profile **live** (live does not exist until tiny-capital phase)
- [ ] Kraken allowlist: `market`, `account`, `paper` / `futures-paper` only
- [ ] No withdraw / funding / transfer tools in any agent profile
- [ ] No main Hyperliquid key on CoS host or VPS agent home — API wallet only later
- [ ] Delegate seats (Claude/Codex/Kimi) inherit **paper profile only**

### Process / hosts
- [ ] No constellation LaunchAgents installed on VPS
- [ ] No IB Gateway / paper-submit / clientId sharing
- [ ] M3 hop: explicit ticket, read-mostly, no clinical cron edits; wipe scratch after
- [ ] CoS laptop is **not** the paper execution host

### Naming (anti-reflex)
- [ ] Avoid product names `ATOM`, `REM`, `ARS`, `Olya` in code paths
- [ ] Prefer `aura`, `trial`, `signal`, `policy`, `paper`

**Fence breach = automatic hard kill + experiment pause pending human review.**

---

## 3. Kraken MCP scope (paper only)

### Intent
Prove CoS loop: data → decision → paper order → PnL → trace → memo, with zero capital and no Singapore Derivatives eligibility dependency.

### Exact MCP services (official `kraken-cli`)
Pin args explicitly — **do not rely on plugin defaults** (sources disagree: some omit `futures-paper`).

| `-s` service | Auth | Phase 1 | Notes |
|---|---|---|---|
| `market` | No | **Allow** | Public ticker/OHLC/book |
| `paper` | No | **Allow** | Spot paper, local sim, live public prices |
| `futures-paper` | No | **Allow** | Futures/perps paper, local sim — **must add explicitly** |
| `account` | Yes | **Omit** until needed | Read-only balances; not required for paper engines |
| `workspace` / `feedback` | No | Optional later | Not required for proving loop |
| `trade` / `futures` | Yes | **Forbid** | Live orders |
| `funding` / `earn` / `subaccount` | Yes | **Forbid** | Withdrawals / transfers |
| `all` | Mixed | **Forbid** | |

**Pinned Phase 1 / Paper invocation:**
```text
kraken mcp -s market,paper,futures-paper
```
Cursor MCP: `"command":"kraken"`, `"args":["mcp","-s","market,paper,futures-paper"]`.

### Paper requirements
- **No API keys, no Kraken account, no auth** for `paper` and `futures-paper`
- Local state; prices from public Spot / Futures APIs
- Spot paper and futures paper are **independent** reset domains
- Labels: spot `"mode":"paper"`; futures `"mode":"futures_paper"`

### Dead-man / cancel-after
- Documented on **live** spot/futures (`order cancel-after`, `futures cancel-after`) — dangerous, needs human ack
- Paper engines: use `cancel` / `cancel-all`; **do not assume** exchange cancel-after heartbeats exist in paper
- **Our risk daemon must implement dead-man** regardless of venue (heartbeat → flatten/cancel-all paper)

### Live gating (for later tiny-capital — not now)
1. Widen `-s` to include `trade` and/or `futures` (explicit human change)
2. Credentials: spot `KRAKEN_API_KEY/SECRET`; futures separate `KRAKEN_FUTURES_*`
3. Dangerous tools need `acknowledged=true` unless `--allow-dangerous` (never enable that for unsupervised)
4. Singapore: Kraken not licensed/regulated in SG; paper is local-only OK. Live Derivatives = separate eligibility check — **do not infer from paper**

### Install gate (after this runbook is approved)
1. Install official `kraken-cli` only (GitHub releases / Cursor marketplace `kraken-cli`); pin version in `ops/kraken_scopes.md`
2. Start with `-s market,paper,futures-paper` only
3. Verify `kraken --version`, public `market` read, `futures-paper` init + one supervised paper order
4. Freeze scope file in repo; never widen without Slim go
5. Load shipped `AGENTS.md` / skills as worker context — still paper-only

Sources: docs.kraken.com/home/mcp, docs.kraken.com/home/cli, github.com/krakenfx/kraken-cli, Cursor marketplace kraken-cli.

## 4. Risk policy draft (paper phase)

Human sets ceilings; risk daemon enforces outside the LLM.

### Hard rules (non-negotiable)
| Rule | Draft default | Notes |
|---|---|---|
| Mode | Paper only | Live MCP absent |
| Max notional per order | TBD by Slim (paper units) | Daemon rejects oversize |
| Max open positions | TBD (start low, e.g. 1–3) | |
| Max daily loss (paper) | TBD % of paper equity | Soft kill on breach |
| Max weekly loss | TBD | Hard kill on breach |
| Leverage cap | Venue paper max **or** lower policy cap | Prefer lower |
| New entries after soft kill | Forbidden until human clear | |
| Withdraw/funding tools | Forbidden | |
| Autopromote to live | Forbidden | |
| Untraced order | Forbidden — treat as hard kill | |

### Kill hierarchy
1. **Soft kill** — pause new entries; leave manages/exits per policy; alert email
2. **Hard kill** — cancel-all paper orders/positions (as API allows); disable order tools in MCP profile; alert
3. **Dead-man** — cancel-after / heartbeat timeout on runner; if CoS or runner silent > N minutes, flatten/cancel

### LLM boundary
- Models may **propose** orders; risk daemon **admits or rejects**.
- Delegates never hold live credentials.
- Spend ceiling for Claude/Codex/Kimi: **TBD by Slim** (weekly USD) — CoS tracks.

### Paper ≠ live honesty
Weekly memo must include a “fidelity risk” section. Kill criterion if we cannot state how paper fills differ from live.

---

## 5. Memo / JSONL templates

### 5.1 Decision event (JSONL — one object per line)

```json
{
  "schema": "aura.decision_event.v1",
  "ts": "2026-08-22T03:00:00Z",
  "trial_id": "T-0001",
  "hypothesis_id": "H-zscore-funding-v0",
  "actor": "cos|worker:<id>|delegate:claude",
  "intent": "open|close|cancel|hold|risk_reject",
  "inputs": {
    "symbols": ["PF_XBTUSD"],
    "features": {},
    "model_note": "short free text"
  },
  "risk_gate": {
    "result": "allow|reject",
    "reasons": [],
    "policy_version": "risk-2026-08-22"
  },
  "venue": {
    "name": "kraken-futures-paper",
    "request": {},
    "response": {},
    "client_order_id": ""
  },
  "fills": [],
  "pnl_delta_paper": null,
  "trace_ref": "path-or-id-to-tool-log",
  "human_auditable": true
}
```

### 5.2 Trial pre-registration (`templates/trial_prereg.md`)

```markdown
# Trial {{id}}
- Hypothesis:
- Family: parametric-stat | funding | breakout | other
- Markets/symbols:
- Data window / as-of:
- Parameters (frozen before run):
- Primary metric:
- Kill criteria for THIS trial:
- Not a look-ahead check: [ ] attested
```

### 5.3 Daily one-pager (`templates/daily_onepager.md`)

```markdown
# Aura daily — {{date}}
- Paper equity / day PnL / max DD:
- Open risk (# positions, notional):
- Orders: proposed / risk-rejected / sent / filled
- Kill-switch state: armed | soft | hard
- Last dead-man heartbeat:
- Top 3 learnings:
- Fence breaches: none | DESC
- Next hypothesis (or HOLD):
```

### 5.4 Weekly memo (`templates/weekly_memo.md`)

```markdown
# Aura weekly — week {{n}}
## Decision: promote | iterate | kill | hold-paper
## CoS / eval health
- Trace coverage %
- Kill drills run / result
- Human review time
- Delegate spend vs ceiling
## Trading (secondary)
- Paper metrics vs baselines (buy-hold / random)
- Fidelity caveats (paper vs live)
## Isolation
- Fence checklist delta
## Asks for Slim
```

### 5.5 LEDGER.yaml (sketch)

```yaml
version: 1
trials:
  - id: T-0001
    status: preregistered | running | banked | grave | null_result
    hypothesis_id: H-...
    started: null
    ended: null
    artifact_dir: evidence/trials/T-0001/
    notes: ""
```

---

## 6. Compute / always-on host (LOCKED)

**Primary always-on: `dexter` (DGX Spark)**  
**Backup: Hetzner CCX/AX** — only if home WAN/power is inadequate while traveling.  
**Not for Phase 1 home:** `playground-dgx` (active Galileo worker), `m4-studio` (offline as of 2026-08-22), M3 clinical.

### Smoke-test facts (2026-08-22)
| Field | Value |
|---|---|
| Reach | From M3: `ssh dexter` → `a8ra_dgx@dexter.local`; Tailscale IP `100.87.225.84` |
| OS | Ubuntu 24.04.4 LTS · **aarch64** |
| CPU / RAM / disk | 20 cores · 119 GiB · 3.6T NVMe (~2.4T free) |
| GPU | NVIDIA GB10 (idle at probe) |
| Load / uptime | ~0.04 · up ~106 days |
| Kraken egress | Spot Time API OK · Futures tickers HTTP 200 |
| kraken-cli | Official **linux ARM64** binary available (e.g. v0.4.1 `aarch64-unknown-linux-gnu`) |

### Role split
| Seat | Host |
|---|---|
| CoS (interactive) | MacBook (Grok Bot) |
| Paper runner + risk + scribe + backtests | **dexter** |
| Extreme sweeps | M3 hop (temporary) or second Spark **only with fence** — prefer not playground |
| Cloud backup | Hetzner (deferred) |

### Access path for CoS (do before bring-up)
MacBook today has SSH aliases only for M3/M4. Add either:
1. `~/.ssh/config` Host `dexter` with `HostName 100.87.225.84`, `User a8ra_dgx`, IdentityFile that M3 already trusts **or** install MacBook pubkey on dexter; or
2. `ProxyJump M3` to `a8ra_dgx@dexter.local`

### Isolation on dexter (mandatory)
- Data root: `/var/aura/` (create with sudo) — **not** under `~/galileo*`, `~/a8ra`, or any constellation checkout
- Dedicated unix user optional but preferred: `aura` with its own home; CoS/automation use that user
- No Galileo workers, no constellation LaunchAgents, no RIVER writes
- systemd units scoped to aura user
- Scratch TTL under `/var/aura/scratch/`

### Concurrency policy (dexter 20c / 119 GB)
**Reserve (highest priority):** OS+metrics 1–2c / 2–4G · paper runner 1–2c / 2–8G · risk 1c / 1–4G · leave ~10–20% idle headroom.  
**Workers:** remainder → roughly **8–12** light backtests or **3–6** heavy multi-GB jobs. Cap by RAM p95 first. Separate cgroup/slice so OOMs kill workers, never risk/paper.

### Provisioning checklist (dexter — after full greenlight)
1. Wire MacBook SSH to dexter (direct Tailscale or ProxyJump)
2. Create `/var/aura/{market,paper,evidence,logs,scratch,secrets}` + perms
3. (Recommended) create user `aura` + sudoers for unit control only
4. Install pinned `kraken-cli` ARM64; MCP `-s market,paper,futures-paper` only
5. systemd: `aura-runner`, `aura-risk`, `aura-scribe`
6. Alert email path + dead-man heartbeat
7. Run kill drills A–C before unsupervised paper

### Hetzner backup trigger
Provision CCX43/AX102 only if: dexter unreachable > agreed SLA while traveling, or Slim wants cloud isolation from a8ra LAN. Until then: **do not purchase**.

## 7. Dry kill-switch drill plan

Run **before** any unsupervised paper loop. Tabletop first, then live paper drill.

### Drill A — Soft kill (tabletop + paper)
1. CoS issues soft kill
2. Runner refuses new entries within 5s
3. Alert email fires
4. JSONL records `intent: risk_reject` / kill event
5. Human clear required to resume

**Pass:** steps 2–4 observed; resume blocked without clear.

### Drill B — Hard kill (paper)
1. Open 1–2 tiny paper positions (supervised)
2. CoS issues hard kill
3. Cancel-all succeeds (or best-effort + alarm if API limited)
4. Order tools disabled in paper profile / runner config
5. Alert + memo artifact

**Pass:** flat or cancelled; no new orders possible until human re-enable.

### Drill C — Dead-man
1. Stop runner heartbeat deliberately
2. Within N minutes (draft **5–15**, Slim picks), risk daemon cancels/flattens and alerts
3. CoS notified

**Pass:** automatic; no human click required for flatten.

### Drill cadence
- Once before paper week 1
- Weekly during paper phase (rotate A/B/C)
- After any MCP scope change

Record results in `evidence/memos/drills/`.

---

## 8. Thin Hyperliquid testnet spike (optional, read-only)

**Gate:** only after S1 paper loop is honest **or** as a **read-only** Phase 1 design spike that cannot place orders.

### Spike scope (design)
- Read-only Info API / testnet URLs
- Document: funding, OI, predicted fundings, liq flags — schema notes
- No agent signing keys on CoS host
- No community MCP installed until reviewed and pinned
- Output: `ops/hl_spike.md` + sample JSON fixtures in `evidence/spikes/hl/` (public data only)

### Explicit non-goals
- No mainnet
- No trading wallet funded for this spike
- No competition with S1 timeline

### When to promote HL to structural track
S1 has ≥2 weekly memos with honest traces AND kill drills green AND human go.

---

## 9. Phase 1 exit criteria → Paper

Greenlight paper only when:
- [ ] Repo exists with layout above
- [ ] Isolation checklist signed off by Slim
- [ ] Kraken paper scope installed and freeze-filed
- [ ] Risk ceilings (TBD items) filled by Slim
- [ ] Templates + LEDGER in repo
- [ ] VPS provisioned; runner/risk/scribe heartbeats visible to CoS
- [ ] Drills A–C passed once
- [ ] Delegate spend ceiling set
- [ ] Alert email path works

---

## 10. Open items for Slim at runbook review

1. Repo/org name — accept `aura` or rename?
2. New GitHub org vs under `SlimWojak`?
3. Fill TBD risk ceilings (notional, daily/weekly loss, max positions, dead-man N)
4. Delegate weekly spend ceiling (USD)
5. Alert email address
6. ~~Hetzner SKU~~ → **deferred** (dexter locked; Hetzner backup only)
7. Approve optional HL read-only spike in parallel with dexter bring-up, or defer entirely?
8. Final greenlight to: create repo → fence dexter → install Kraken paper connector
9. Approve MacBook SSH path to dexter (pubkey install vs ProxyJump)

---

## Appendix A — Kraken service pin (confirmed for runbook)

```text
# Paper-only MCP (CoS + VPS agents)
kraken mcp -s market,paper,futures-paper

# Explicitly never in Phase paper
# trade | futures | funding | earn | subaccount | all | --allow-dangerous
```

Pin installed CLI semver in `ops/kraken_scopes.md` at install time (command counts drift across releases).

## Appendix B — Hetzner SKU pin (BACKUP ONLY — not Phase 1 primary)

| SKU | Spec | ~EUR/mo excl. VAT | Role |
|---|---|---|---|
| **CCX43** | 16 dedicated vCPU / 64 GB / 360 GB NVMe | ~€276 EU · ~€341 SIN | **Default cloud start** |
| **CCX53** | 32 / 128 GB / 600 GB NVMe | ~€533 EU · ~€652 SIN | Scale-up |
| **AX102-1** | 16c 7950X3D / 128 GB / 2×NVMe (Robot, EU) | ~€257 + setup | Best €/perf if EU metal OK |
| CCX63 | 48 / 192 GB | higher | Overshoot |

Sources: docs.hetzner.com price-adjustment (15 Jun 2026), hetzner.com/cloud/general-purpose, dedicated AX102, cloud locations (fsn1/nbg1/hel1/ash/hil/sin).

