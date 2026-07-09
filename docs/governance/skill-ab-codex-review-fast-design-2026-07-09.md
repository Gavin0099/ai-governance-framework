# Minimal A/B — `codex-review-fast` (with-skill vs without-skill)

> Design / pre-registration only. Read-only. No run yet. No gate / hook / CI / enforcement.
> Method: SkillsBench-style paired evaluation (matched no-skill vs with-skill on one fixed task with a deterministic verifier).
> Purpose: produce the **first real `decision_effect` evidence** for a local skill, turning "measure before keep" into one measured ledger entry.

## Subject

- Skill: `.agents/skills/codex-review-fast` (current ledger status: `investigate` / `evidence_needed`).
- What the skill claims to add: two independent review passes (correctness/regressions + architecture/risk/missing-evidence), findings-not-summary, preserve disagreements. Priorities: bugs, behavioral regressions, architecture drift, missing/weak evidence, test gaps, over-broad scope.
- **Target harness (pre-declared, per skill-governance rule):** results are scoped to ONE named harness (e.g. Codex). A result on this harness does **not** transfer to Claude/Copilot without a separate run.

## Fixed task (pre-registered ground truth)

One review target: a single small diff containing **K = 6 pre-seeded, known defects**, drawn from `docs/e1-mutation-catalog.md` classes so seeds are realistic and reuse existing catalog. The 6 are chosen to exercise the skill's own stated priorities (not just easy syntax bugs):

| # | defect class | maps to skill priority |
|---|---|---|
| 1 | boundary flip (`>` → `>=`) | bug / correctness |
| 2 | reversed condition | bug / correctness |
| 3 | removed guard clause | behavioral regression |
| 4 | off-by-one loop bound | bug / correctness |
| 5 | missing test for the changed behavior | test gap / missing evidence |
| 6 | change touches behavior outside stated scope | over-broad scope |

**Before any run, pre-register (commit + timestamp):**
- exact `file:line` + defect type + the expected finding wording, for all 6;
- an **allowlist** of legitimate code regions in the diff (so false positives are scored only against agreed-legitimate lines);
- the chosen target module + the diff itself.

Instantiation note: pick one small, self-contained module as the target; construct the diff so each seeded defect is independently detectable. Exact `file:line` is filled in at instantiation and frozen before the first run.

## Two conditions (matched)

Identical model, diff, settings/temperature, and requested output format (`findings as file:line + type`); **fresh context per condition** (skill loaded only in B; no cross-condition contamination).

- **A — no-skill:** plain prompt "Review this diff and list problems as file:line + type."
- **B — with-skill:** same prompt, `codex-review-fast` invoked (its two-pass findings workflow).

## Fixed rubric (deterministic, machine-executable)

Scoring is done by a **fixed script** (`skill_ab_scorer.py`, committed with this note). A reported finding matches a seeded defect only if ALL hold:

1. **Line:** finding line `L_f` and registered line `L_r` satisfy `|L_f − L_r| ≤ 1` **in the same file**; if no line within ±1, a **fallback regex anchor** (pre-registered per defect, e.g. the literal token `>=` for defect #1, the guard signature for #3) matching inside the same function body counts as a line match.
2. **Type:** finding's defect type equals the registered type, using a **pre-registered alias table** (e.g. `off-by-one ≡ loop-bound-error`; `over-broad-scope ≡ out-of-scope-change`). No credit for the right line with the wrong type.
3. **One-to-one:** each seeded defect is matched by at most one finding (first by line order); extra findings on an already-matched defect are ignored (neither TP nor FP).

Then:
- **TP** = seeded defect matched per above
- **FN** = seeded defect with no match (FN = 6 − TP)
- **FP** = finding matching no seeded defect **and** landing on an allowlisted-legitimate line (findings landing off both the defect set and the allowlist are recorded as `unscored`, not FP — the allowlist bounds FP to agreed-legitimate code)
- Per run: `recall = TP / 6`; `precision = TP / (TP + FP)`, **defined as `n/a` when `TP + FP = 0`** (no findings) and excluded from precision aggregation (that run still contributes `recall = 0`).

The scorer consumes only: frozen ground-truth file, frozen allowlist, and the raw findings file per run. It emits the per-run table below.

## Freeze & integrity (tamper-evidence)

The pre-registration commit records, in a sidecar `skill-ab-codex-review-fast.frozen.json`:

- `defects_sha256` — SHA-256 of the frozen ground-truth defect file
- `allowlist_sha256` — SHA-256 of the frozen allowlist file
- `diff_sha256` — SHA-256 of the target diff under review
- `scorer_commit` — commit id of `skill_ab_scorer.py` (produced and frozen at instantiation / execution step 1, **not** in this design commit; this note commits the protocol only)

**Enforcement:** before scoring, the scorer recomputes these hashes from the live files and **asserts they equal the frozen values**; any mismatch aborts scoring and marks the run `invalid`. This makes any post-run edit of ground truth / allowlist / scorer detectable — "committed first" is upgraded to "provably unchanged since freeze."

## Controls (anti-gaming / claim discipline)

- **Pre-registration:** defect list + allowlist + rubric + thresholds + scorer committed **before** any run; bound by the hashes above.
- **Scorer separation (cross-session):** the scorer is a **deterministic script**, not a model. It is run in a **separate session from the A/B producers**, on findings files whose **condition labels are stripped and order shuffled**. No agent that produced A or B output participates in scoring. (Optional second check: an independent operator re-runs the same script; byte-identical output expected.)
- **Fixed run config (recorded per run):** model id + version pinned; `temperature = 0` (or the lowest deterministic setting the harness allows, recorded); fixed max-output-tokens; fixed tool options; **fresh context per run** (skill loaded only in B). All recorded in the per-run table.
- **N = 3 per condition**, single sitting, one model/version across A and B.

## Per-run reporting (raw, not just means)

The result artifact MUST include this table (all 6 runs, raw):

| run_id | condition | model@version | temp | TP | FN | FP | recall | precision |
|--------|-----------|---------------|------|----|----|----|--------|-----------|
| … | A | … | 0 | … | … | … | … | … |

Aggregates (`mean(recall)`, `mean(precision over defined runs)`, min/max) are computed **from this table by the scorer**, never hand-entered.

## Decision rule → `decision_effect` (explicit formulas, pre-committed)

Let `ΔR = mean(recall_B) − mean(recall_A)` and `ΔP = mean(precision_B) − mean(precision_A)` (precision means over runs where precision is defined). The scorer emits `ΔR`, `ΔP`, and the verdict by these exact rules, evaluated top-down:

- **positive** ⟺ `ΔR ≥ 0.15` **AND** `ΔP ≥ −0.10`
  → promote `codex-review-fast` `evidence_needed` → `keep_observe (evidenced)`; write `decision_effect = positive`, this artifact as `evidence_ref`.
- **negative** ⟺ `ΔR < 0.15` **AND** `ΔP < −0.10` (skill adds false-positive cost without a recall gain)
  → `decision_effect = negative`; retire/downgrade candidate.
- **none** ⟺ otherwise (`ΔR < 0.15` and `ΔP ≥ −0.10`)
  → `decision_effect = none`; downgrade/merge candidate.

Thresholds (`0.15`, `−0.10`) are frozen here before any run; the verdict is a pure function of the per-run table, not a judgement call.

## Outputs (into existing ledger — no new table)

- Result artifact: TP / FN / FP / recall / precision per condition, per run + mean.
- Write the measured `decision_effect` into the `codex-review-fast` entry in `governance-surface-maintenance-queue.v0.1.json` (+ inventory), replacing the `evidence_needed` placeholder.
- This is the ledger's **first real, measured `decision_effect`**.

## Claim ceiling

Single seeded diff, N = 3, one model/harness. Measures **catch-rate on one constructed review task**, not general review quality. A positive result means "supported on this task/harness," **not** "proven broadly" (real PRs, other languages, other harnesses each need their own run). Explicitly **not** a gate; measurement only.

## Non-goals

- No hook / CI / gate / enforcement.
- No skill edits.
- No baseline / managed-block change.
- No claim of runtime adoption.

## Next execution steps (after this pre-registration is committed)

1. Pick target module + build the diff; fill exact `file:line` for all 6 defects + allowlist; commit (freeze ground truth).
2. Run A ×3 and B ×3 (fresh context each), collect raw findings.
3. Score blind against frozen ground truth; compute recall/precision means.
4. Apply decision rule; write `decision_effect` into the ledger entry with this artifact as evidence.
