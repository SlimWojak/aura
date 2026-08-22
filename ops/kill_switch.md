# Kill-switch drills

See docs/phase1-runbook.md §7.

All commands are human-triggered and paper-only. There is no systemd daemon in
this PR and no live Kraken scope. Run on dexter from the repo checkout with
`AURA_ROOT=/var/aura` unless testing against a temporary root.

## Status

```bash
python3 -m runtime.tools.kill_drill status
```

Shows:

- `${AURA_ROOT:-/var/aura}/paper/kill_state`
- `${AURA_ROOT:-/var/aura}/paper/heartbeat` age
- `kraken futures paper status -o json`
- `kraken futures paper positions -o json` with an open-position summary

## A — soft kill

Soft kill pauses new supervised entries and does **not** flatten existing paper
positions:

```bash
python3 -m runtime.tools.kill_drill soft
python3 -m runtime.tools.kill_drill drill-a
```

`drill-a` writes `soft`, attempts a tiny supervised paper buy, and passes only
when `runtime.risk.admit()` rejects with `kill_state soft`. It leaves the kill
state soft for human review. To re-arm after the drill:

```bash
python3 -m runtime.tools.kill_drill drill-a --rearm
```

Manual clear:

```bash
python3 -m runtime.tools.kill_drill arm
# or delete the file and rely on default armed:
python3 -m runtime.tools.kill_drill arm --delete
```

## B — hard kill

Hard kill writes `hard`, calls futures paper cancel-all, then flattens open
futures paper positions using opposite-side market orders. It is the explicit
kill override path and does not call `admit()` for the flatten orders because
normal admission is intentionally blocked while `kill_state=hard`.

Required acknowledgement:

```bash
python3 -m runtime.tools.kill_drill hard --i-understand-paper
```

Hard drill:

```bash
python3 -m runtime.tools.kill_drill drill-b --i-understand-paper
```

If flat, `drill-b` opens one tiny supervised paper buy first, then hard-kills and
verifies open positions are zero. To avoid opening a position when already flat:

```bash
python3 -m runtime.tools.kill_drill drill-b --skip-open --i-understand-paper
```

Optional re-arm after verification:

```bash
python3 -m runtime.tools.kill_drill drill-b --rearm --i-understand-paper
```

## C — dead-man check

Heartbeat:

```bash
python3 -m runtime.tools.kill_drill heartbeat
```

One-shot dead-man check:

```bash
python3 -m runtime.tools.kill_drill deadman-check
```

The check compares heartbeat age with `RISK_POLICY` dead-man seconds (600). A
stale or missing heartbeat invokes the hard-kill path. This is only a command for
future scheduling; do not install a background daemon or systemd unit in this
phase.

## Evidence

Kill/drill ops events use schema `aura.kill_event.v1` and append to the same
trial JSONL shape as decisions:

```text
${AURA_ROOT:-/var/aura}/evidence/trials/T-kill-.../decision.jsonl
```

Supervised drill attempts still append `aura.decision_event.v1` entries to that
trial. Mixed schemas are expected for kill drills.
