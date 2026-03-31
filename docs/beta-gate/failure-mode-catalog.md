# Beta Gate Failure Mode Catalog

> Status: active
> Created: 2026-03-30
> Purpose: canonical record of observed onboarding failures, used to classify
> whether a new reviewer run is reproducing a known failure or surfacing a new one.

---

## How to use this catalog

When a reviewer run produces a failure, check here first:

1. Does the failure match a known entry? Record as reproduction and note any variance.
2. Does it not match? Add a new entry, do not force-fit into an existing one.

Do not merge distinct failures into one entry just to keep the catalog tidy.
A false merge hides signal.

---

## FM-001: No-Python Execution Block

**First observed:** R2 reviewer run, 2026-03-30

**Observation:**

```text
Commands attempted:
  python --version  - not found
  python3 --version - not found
  py --version      - not found / no installed Python

Result: all documented execution steps blocked at prerequisites.
No governance artifact produced.
```

**Classification:** Onboarding Blocking (Friction subtype)

Not classified as simple Friction because it blocked the entire execution path
with no recovery route at the time. Distinguished from ordinary friction by:

- affects all tools, not one command
- no documented bypass existed
- reviewer stopped onboarding, not just skipped a step

**CP affected:** CP5 (artifact production)

**Gate impact:** Hard Fail, triggers automatic Gate FAIL regardless of other CP scores.
See `onboarding-pass-criteria.md` Gate override rules.

**Mitigation:** Route B (no-Python onboarding evidence branch)

- Defined in: `start_session.md` Prerequisites -> Route B
- Template: `docs/no-python-onboarding-evidence.md`
- Reviewer brief: `docs/beta-gate/reviewer-route-b-brief.md`

**Mitigation status:** Deployed. Pending live validation run.

**Variance notes:**
If a future run hits a different execution blocker, for example wrong shell,
permission denied, or missing repo files, check whether it matches this entry:

| Dimension | FM-001 | Different failure? |
|-----------|--------|--------------------|
| All python variants unavailable | Y | N -> check FM-002+ |
| Failure is at prerequisites before any tool runs | Y | N -> may be a different FM |
| No artifact produced | Y | N -> may be partial, not total block |
| Reviewer had no documented recovery path | Y at time of run | N -> Route B exists now |

---

## FM-002: README Entry Density / Slow Orientation

**First observed:** R2 reviewer run, 2026-03-30 (also noted in R1 run)

**Observation:**

```text
File: README.md
Expected: Short reviewer-first path, clear first step
Observed: Dense overview with architecture, release, trust-signal, runtime,
          domain-contract, and adoption content mixed together.
          Pointer to start_session.md present but required scanning.
Time to orient: 3-5 minutes
```

**Classification:** Friction

Does not block onboarding. Reviewer eventually found the entrypoint.
Classified as Friction, not Structural, because the pointer exists.
It is just not surfaced early enough.

**CP affected:** CP1 (entry point found), borderline pass, not fail.

**Gate impact:** None. CP1 still passed within the time limit.

**Mitigation:** Not yet applied. Lowest-cost fix would be a short
"start here" block at the top of README.md above the architecture overview.

**Mitigation status:** Unresolved. Low urgency while CP1 is still passing.

---

## Entries pending

No further failures observed. Add entries here as new reviewer runs produce
new failure patterns.
