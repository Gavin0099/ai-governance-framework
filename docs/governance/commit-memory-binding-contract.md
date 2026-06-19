# Commit-Memory Binding Contract v0.1

Status: advisory reviewer-facing contract. Doc/spec-only. Not enforced.

Derived from:
- `docs/governance/checkpoint-memory-audit-spec.md` (the detector)
- `docs/governance/agent-runtime-integration-boundary.md` (§4 ordering discipline)
- `docs/REVIEWER_ENTRYPOINT.md` (claim-class reading)
- Reproduced `checkpoint_memory_audit --last 3` findings at HEAD `78135b7`

## Position in the ordering (do not skip)

```
visibility audit (done) → THIS contract (interpretation) → (later) blocker
```

This is **step 2**. It defines *how to read* checkpoint-audit findings; it does
not enforce anything and does not change tool behavior. Jumping to a blocker now
would repeat the "log != authority" error: blocking before the binding contract
exists.

## 1. What this contract is — and what stays out of it

- It is the **policy source** for interpreting checkpoint-audit findings.
- The audit tool stays **policy-free**: it reports divergence; it does not decide
  which divergence is acceptable. *This document decides.* No exception may be
  hard-coded into the tool — that would make the tool a silent policy source.
- It is **advisory**: no commit is blocked. v0.1 defines interpretation plus the
  maturity conditions that would gate any future enforcement.

## 2. Commit-class taxonomy (binding expectation per class)

| Commit class | Memory binding expectation | Rationale |
|---|---|---|
| **Claim-bearing** — `feat`/`fix`, or a governance contract / decision-boundary / claim-surface change | **SHOULD** have a commit-bound memory record | it changes what the repo can claim |
| **Docs / non-claim** — typo, formatting, link, comment-only | **Optional** | no claim-surface change |
| **Memory commit** — `docs(memory): …` | **MUST NOT** require its own downstream memory | regress guard; the commit *is* the record |
| **Generated / runtime-ledger** — snapshot, receipt, ledger append | **No** memory required | not a claim |
| **Merge / revert** | Out of scope in v0.1 | needs its own treatment |

"SHOULD" here is an advisory expectation, not a gate. Absence on a claim-bearing
commit is a *signal to reconcile*, not a violation.

## 3. Worked examples (from the reproduced window)

- `78135b7 docs(memory): record checkpoint audit push` → **memory commit** →
  `commit_without_memory` here is **expected advisory noise**. A memory-recording
  commit needing its own memory is infinite regress. No action.
- `4952be6 docs(governance): boundary + skill claim-class spec` → **claim-bearing**
  (governance docs that change the claim surface) → a commit-bound memory record
  **SHOULD** exist. Its absence is a **real advisory gap to reconcile**, not noise.

## 4. Post-push memory-only commits

A memory-recording commit does not itself require a downstream memory record.
`commit_without_memory` on a `docs(memory)` commit is expected advisory noise and
must not be treated as a gap. (This is the regress guard, stated as policy so the
tool need not encode it.)

## 5. WORKTREE / NO_COMMIT promotion reconciliation

A `WORKTREE` / `NO_COMMIT` entry is a working placeholder. It SHOULD be reconciled
with a corrective commit-bound record only when **both** hold:

1. the work it describes later lands as a real commit, **and**
2. the entry carries a claim that matters (claim-bearing).

Pure working notes that never become a claim need not be promoted.
`stale_no_commit_memory` is the *signal*; promotion is the *resolution*; not every
instance is an obligation. (The three findings in `2026-06-19.md` L4/L16/L28 are
candidates to evaluate against this rule, not automatic debts.)

## 6. Finding interpretation — noise vs signal

| Finding | Treat as **noise** when | Treat as **signal** when |
|---|---|---|
| `commit_without_memory` | commit is memory / generated / merge | commit is claim-bearing |
| `stale_no_commit_memory` | no real commit followed (still a placeholder) | a real commit followed **and** the claim matters |
| `unreceipted_validation` | in out-of-window historical memory (baselined debt) | in current-window, claim-bearing memory |
| `rollup_memory_divergence` | — | any (rollup commits should reflect to memory) |
| `consumer_uninstalled` | — | any consumer in scope without install |

Note on `unreceipted_validation=37` in `--last 3`: these scan memory content from
prior days (06-03…06-06), not the three windowed commits. They are **baselined
historical debt**, not this-slice signal, and are out of scope for any current
slice unless explicitly triaged.

## 7. Maturity conditions before enforcement (gate to step 3)

A blocker may be **considered** only when **all** hold:

1. the commit-class taxonomy (§2) is stable — no churn across N consecutive windows;
2. historical debt is **baselined** — a frozen baseline so a future gate measures
   *new* drift only, never pre-existing debt;
3. false-positive rate ≈ 0 on a defined window for the specific class to be enforced;
4. a **ratified authority** owns this contract (per the repo authority hierarchy) —
   not the audit tool, not the generating agent;
5. the `consumer_uninstalled` gap is resolved for repos in enforcement scope.

Until every condition holds, the correct state is **advisory only**.

## Claim ceiling

```yaml
claim_ceiling:
  - advisory interpretation contract only (v0.1)
  - no tool behavior change; tool stays policy-free
  - no hook, no CI, no blocker, no enforcement
not_claimed:
  - that any commit is required to have a memory record (no enforcement exists)
  - that historical unreceipted_validation debt is resolved or baselined yet
  - that the audit tool enforces or encodes this contract
  - that the §7 maturity conditions are met today
```
