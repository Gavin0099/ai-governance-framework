# Reviewer Brief — Route B Live Run

> Version: 1.0
> Created: 2026-03-30
> Purpose: Gate re-run for Beta Gate Condition 2 (CP5)
> Required environment: Python unavailable on PATH

---

## What this run is for

A previous reviewer run (R2, 2026-03-30) produced a Gate Verdict of FAIL.
The failure was CP5: no governance artifact could be produced because Python was
unavailable and no recovery path existed.

Route B has since been added. This run verifies that Route B works as a real
onboarding path — not a retroactive reconstruction, but a live fill under
actual constraints.

**This run is the Gate re-run. Its output is the CP5 evidence.**

---

## Your environment constraint

You must be in an environment where `python`, `python3`, and `py` are all
unavailable on PATH.

Verify this before starting:

```
python --version   → should fail
python3 --version  → should fail
py --version       → should fail
```

If any of these succeed, this run does not qualify as a Route B run.
Stop and find a different environment or disable the Python executable for
the duration of the run.

---

## Starting point

https://github.com/Gavin0099/ai-governance-framework

Open that URL in a browser. Do not clone the repo unless a file explicitly
tells you to.

---

## Your task

1. Follow `start_session.md` from the top
2. When you reach the Prerequisites section and all Python commands fail,
   follow the Route B instructions in that file
3. Copy the template at `docs/no-python-onboarding-evidence.md`
4. Fill in every field — live, as you go
5. Save your completed artifact as `docs/no-python-evidence-<YYYY-MM-DD>.md`

---

## Ground rules

- **Only follow what the docs say.** Do not infer or reconstruct from context.
- **Fill the template as you go.** Do not reconstruct from memory at the end.
- **Record exact output.** For failed commands, copy the literal terminal message.
- **Do not ask the author.** If the docs do not tell you what to do next, that
  is a failure worth recording in section 6.
- **Section 1b is a gate.** If you cannot locate both files named there, stop
  and record the failure before continuing.

---

## What a passing artifact looks like

When you are done, your completed file should satisfy all three validity
conditions in the template's "Artifact validity" section:

1. All seven sections filled (no blank fields)
2. Section 6 records exact failure output, not a paraphrase
3. Section 7 contains a concrete next step, not "install Python"

If your file meets these three conditions, it is a valid Route B artifact and
CP5 is considered resolved for this environment.

---

## After you finish

File your completed artifact at:

```
docs/no-python-evidence-<YYYY-MM-DD>.md
```

That file is the Gate re-run evidence. The author will review it against the
pass criteria in `docs/beta-gate/onboarding-pass-criteria.md` and update the
Gate verdict.

---

## For the author — Gate judgment checklist

Do not judge this run until you can answer all three questions from the artifact alone,
without asking the reviewer:

1. **Environment was genuinely constrained.**
   Did the reviewer enter Route B because all Python variants returned
   "command not found" — not because Route A looked inconvenient?
   Evidence: Section 1 exact output + Section 6 blocker record.

2. **Failure is classifiable against the catalog.**
   Does the failure in Section 6 match FM-001 (no-Python block), or is it
   a new pattern not yet in `docs/beta-gate/failure-mode-catalog.md`?
   If new: add an entry before closing the run.

3. **Route B was not self-selected.**
   Is there evidence the reviewer attempted Route A before arriving at Route B?
   (Section 1 commands attempted, Section 6 blocker record.)
   If Route B was entered without attempting `python`, `python3`, and `py`,
   the run does not qualify as a valid Route B run.

If any question cannot be answered from the artifact, the run is incomplete —
request a clarification or treat it as a new FM rather than closing CP5.
