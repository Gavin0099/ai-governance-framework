# No-Python Onboarding Evidence Template

> Use this template when `python`, `python3`, and `py` are all unavailable in your environment.
> Fill in every field. Save the completed file as `docs/no-python-evidence-<YYYY-MM-DD>.md`.
> This file is a formal onboarding artifact, not a workaround.

---

## 1. Environment record

```
Date:
Operating system:
Shell / terminal used:

Commands attempted (copy exact output or "command not found"):
  python --version:
  python3 --version:
  py --version:
```

---

## 1b. Repo identity check

**Complete this before filling in sections 2–5. If either file cannot be found, stop and record the failure in section 6.**

In the repo you are reviewing, find these two files and confirm they exist:

```
File 1 — onboarding entrypoint:
  Relative path as you see it (e.g. start_session.md or docs/start_session.md):
  Confirmed it exists (Y / N / cannot find):
  First heading or first sentence of the file:

File 2 — drift checker:
  Relative path as you see it:
  Confirmed it exists (Y / N / cannot find):
  What does the first --help line or opening docstring say it does?
```

If either file is missing or the content does not match what sections 2–5 describe, you are either in the wrong repo or looking at an incomplete adoption. Do not continue filling sections 2–5 until this is resolved.

---

## 2. Entrypoint verification

Read `README.md`. Answer:

```
What does this framework do, in one sentence?

What file does README.md say to open first for onboarding?

Did you find that file?  Y / N
If N, where did you look and what did you find instead?
```

---

## 3. Adoption path verification

Read `start_session.md`. Answer:

```
What is the canonical adoption command?

What tool does it use? (name the script, not just "python")

What does adoption produce in the target repo? (name at least one file or artifact)

Is there a fallback adoption path if Python is unavailable?  Y / N
If Y, what is it and what does it require?
```

---

## 4. Minimum session flow verification

Read `start_session.md`. Answer:

```
List the steps of the minimum governance session flow in order:
1.
2.
3.
4.

Which step requires execution to verify?

Which steps can be verified by reading only?
```

---

## 5. Drift check verification

Read `README.md` or `governance_tools/README.md`. Answer:

```
What command checks for governance drift?

What does it check? (describe in one sentence — not the command, the behavior)

Where is that tool located in the repo?
```

---

## 6. Blocker record

```
At what step did execution become required to continue?

Exact command that failed:

Exact failure output (or "command not found"):

Was there a documented recovery path for this failure?  Y / N
If Y, what was it?
If N, where in the docs did the path end?
```

---

## 7. Onboarding verdict

```
Task 1 — understand what this is for:         Y / N / Partial
Task 2 — understand how adoption works:       Y / N / Partial
Task 3 — describe minimum session flow:       Y / N / Partial
Task 4 — find the drift checker:              Y / N / Partial

Recommended next step to unblock execution:
```

---

## Artifact validity

A completed copy of this template is a valid Route B onboarding artifact if:

- All seven sections are filled in (no blank fields)
- Section 6 records the exact failure, not a paraphrase
- Section 7 contains a concrete next step, not "install Python"

A template with blank fields or a section 7 that only says "install Python" does not count as a completed artifact.
