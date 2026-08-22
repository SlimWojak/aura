# Aura delegates on dexter

How CoS (Grok Bot) invokes on-box builders. Paper-only. See [DISPATCH.md](../docs/DISPATCH.md) and [BUILD_PLAN.md](../docs/BUILD_PLAN.md).

Host: `dexter` (`a8ra_dgx@100.87.225.84`)  
Repo: `~/aura` · Data: `/var/aura` · Kraken futures paper: CLI-only

## Inventory (2026-08-22)

| Tool | Path | Version |
|---|---|---|
| Claude Code | `~/.local/bin/claude` | 2.1.239 |
| Droid (Factory) | `~/.local/bin/droid` | 0.120.1 |
| Kraken CLI | `~/.cargo/bin/kraken` | 0.4.1 |
| uv / python3.12 | `~/.local/bin/` | present |

PATH for non-interactive SSH should include `~/.local/bin` and `~/.cargo/bin` (bashrc/profile updated). Prefer absolute paths from automation.

## When to use which

| Job | Delegate |
|---|---|
| Implement/fix runtime against `/var/aura` + Kraken paper | **Claude** or **Droid** on dexter |
| Repo-only PR (docs, schemas, stubs) | **Cursor cloud agent** (not dexter IDE) |
| Deep review / critique while traveling | Claude or Codex on **MacBook** |
| Market/paper smoke | `kraken` on dexter (or CoS Kraken MCP spot paper) |

## Hard rules for every dexter delegate

1. Work only under `~/aura` and `/var/aura` — never constellation / RIVER clinical / Galileo paths.
2. Paper only — never widen Kraken to live scopes (`trade`, `futures`, `funding`, `earn`, `subaccount`, `all`).
3. Futures paper = `kraken futures paper …` CLI. Spot MCP = `market,paper` only.
4. Produce artifacts: commits/PRs, JSONL under `/var/aura/evidence`, or memos. No silent “done”.
5. Risk admission is policy/code — LLM proposes, does not bypass RISK_POLICY.md.
6. Spend ceiling for API delegates: see RISK_POLICY.md (USD 50/week default).

## Invoke recipes (SSH from MacBook / CoS)

```bash
# shell on dexter
ssh dexter

# Claude Code in repo (interactive)
cd ~/aura
claude --version
claude   # then give a paper-only, fence-bound task

# Droid
cd ~/aura
droid --version
droid    # Factory agent session in-repo
```

Non-interactive / CoS-driven pattern (preferred for automation):

```bash
ssh dexter 'cd ~/aura && ~/.local/bin/claude -p "PAPER ONLY. Fence: no constellation, no live Kraken. Task: …"'
```

Exact Claude non-interactive flags evolve — prefer `claude --help` on box before baking flags into routines. Always include the paper/fence preamble in the prompt.

Droid:

```bash
ssh dexter 'cd ~/aura && ~/.local/bin/droid exec --help'  # confirm local exec UX
```

Document the stable Droid one-shot flag here once confirmed in a supervised session.

## Auth notes

- Claude may need a one-time `claude auth login` (or equivalent) on dexter if API calls fail — Slim completes that in an interactive SSH session; CoS never handles passwords.
- Droid auth lives under `~/.factory/` (already present on dexter).
- Deploy key `github-aura` is configured for `~/aura` push/pull.

## Smoke checklist after install

- [ ] `ssh dexter '~/.local/bin/claude --version'` → 2.1.239+
- [ ] `ssh dexter '~/.local/bin/droid --version'` → 0.120.1+
- [ ] `ssh dexter '~/.cargo/bin/kraken futures paper status -o json'` → paper mode
- [ ] Claude can read `~/aura/AGENTS.md` in a short supervised prompt without touching live scopes

## Out of scope on dexter

- Cursor IDE / Cursor CLI — use cloud agents for PRs
- Codex — optional later; not required for P0/P1
