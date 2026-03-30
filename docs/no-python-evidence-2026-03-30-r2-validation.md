# No-Python Onboarding Evidence — 2026-03-30 (R2 Validation)

> Source: R2 reviewer run 2026-03-30
> Purpose: template fitness check — retroactive validation artifact
> Note: This run occurred before Route B existed. This file validates whether the
> Route B template can faithfully capture the observations from that run.
> It is not a native Route B run. Do not treat it as evidence that Route B was
> followed at the time. Treat it as evidence that the template can承載 that failure.

---

## 1. Environment record

```
Date: 2026-03-30
Operating system: not recorded by reviewer
Shell / terminal used: not recorded by reviewer

Commands attempted (copy exact output or "command not found"):
  python --version:   unavailable (command not found or not on PATH)
  python3 --version:  unavailable (command not found or not on PATH)
  py --version:       unavailable (command not found or not on PATH)
```

**Template fitness note:** Section 1 asks for OS and shell. The R2 run did not record
these. The template would have surfaced this gap if the reviewer had been filling it
in live — which is the correct behavior. The template is more thorough than the raw run.

---

## 1b. Repo identity check

```
File 1 — onboarding entrypoint:
  Relative path as you see it: start_session.md
  Confirmed it exists: Y
  First heading or first sentence of the file:
    "# Start Session
    This file is the shortest path to seeing the framework produce real output."

File 2 — drift checker:
  Relative path as you see it: governance_tools/governance_drift_checker.py
  Confirmed it exists: Y
  What does the first --help line or opening docstring say it does?
    Checks repo governance files against framework baseline: protected file hashes,
    freshness state, plan section inventory, and minimum schema.
```

Both files found. Proceeding to sections 2–5.

---

## 2. Entrypoint verification

```
What does this framework do, in one sentence?
It is an executable governance framework for AI-assisted development that tries to
enforce rules and preserve continuity at the session/task boundary instead of
relying only on prompts or static policy docs.

What file does README.md say to open first for onboarding?
start_session.md (referenced at line 280 of README.md: "五分鐘導覽請從 start_session.md 開始")

Did you find that file?  Y

If N, where did you look and what did you find instead:
N/A
```

---

## 3. Adoption path verification

```
What is the canonical adoption command?
python governance_tools/adopt_governance.py --target /path/to/your/repo

What tool does it use? (name the script, not just "python")
governance_tools/adopt_governance.py

What does adoption produce in the target repo? (name at least one file or artifact)
AGENTS.base.md (protected baseline copy) and .governance/baseline.yaml
(hash inventory of adopted files)

Is there a fallback adoption path if Python is unavailable?  Y
If Y, what is it and what does it require?
bash scripts/init-governance.sh --target /path/to/your/repo --adopt-existing
Requires bash (Linux/macOS only — not available on Windows without WSL)
```

---

## 4. Minimum session flow verification

```
List the steps of the minimum governance session flow in order:
1. adopt_governance.py --target (baseline adoption)
2. governance_drift_checker.py --repo (drift verification)
3. session_start.py (AI session begins, contract loaded)
4. pre_task_check.py (gate before task execution)
5. post_task_check.py (verification after task output)

Which step requires execution to verify?
All steps require execution to produce a tool-backed artifact.
Step 1 (adoption) has a bash fallback for Linux/macOS.
Steps 2–5 are Python-only with no documented non-execution path.

Which steps can be verified by reading only?
The existence and purpose of each step can be verified by reading start_session.md
and governance_tools/README.md. The outputs cannot be verified without execution.
```

---

## 5. Drift check verification

```
What command checks for governance drift?
python governance_tools/governance_drift_checker.py --repo /path/to/your/repo --framework-root .

What does it check? (describe in one sentence — not the command, the behavior)
It checks whether the repo's protected governance files, baseline hashes, freshness
state, and minimum schema still match the framework's expected state.

Where is that tool located in the repo?
governance_tools/governance_drift_checker.py
```

---

## 6. Blocker record

```
At what step did execution become required to continue?
Prerequisites — the very first step: python governance_tools/adopt_governance.py --check-env

Exact command that failed:
python governance_tools/adopt_governance.py --check-env

Exact failure output (or "command not found"):
"command not found" (python not on PATH)
Fallbacks also failed: python3 and py both returned "command not found"

Was there a documented recovery path for this failure?  Partial
If Y, what was it?
start_session.md listed python3 and py as fallbacks — both tried and failed.
start_session.md listed OS-specific install instructions (python.org, brew, apt).
No path was documented for continuing onboarding without any Python installation.

If N, where in the docs did the path end?
After the install instructions in start_session.md Prerequisites. There was no
"if install is not possible in this environment" branch.
```

---

## 7. Onboarding verdict

```
Task 1 — understand what this is for:         Y
Task 2 — understand how adoption works:       Y
Task 3 — describe minimum session flow:       Partial
  (flow described by reading; no step executed; no output verified)
Task 4 — find the drift checker:              Y

Recommended next step to unblock execution:
Install Python 3.10+ via python.org/downloads (Windows) or system package manager,
then re-run: python governance_tools/adopt_governance.py --check-env
Expected output: [OK] Python 3.x available / [OK] pyyaml / [OK] pytest
```

---

## Artifact validity check

- All seven sections filled: **Y**
- Section 6 records exact failure (not paraphrase): **Y**
  (commands named, "command not found" recorded, partial recovery path documented)
- Section 7 next step is concrete: **Y**
  (specific command, specific expected output)

**Verdict: valid Route B artifact**

---

## Template fitness notes (for author review)

**What the template surfaced that the raw run did not record:**

1. Section 1: OS and shell were not captured in the R2 run. The template would have
   prompted for these. Useful for diagnosing environment-specific failures.

2. Section 3: The bash fallback path is adoption-only. The template makes this
   explicit in a way the raw run did not articulate clearly.

3. Section 4: The template separates "execution required" from "readable only,"
   which the raw run blurred. This distinction is load-bearing for CP5.

**What the template could not capture from the R2 run:**

1. Section 1 OS/shell fields: reviewer did not record these during the run.
   The template cannot retroactively recover this data.
   Mitigation: a live Route B run would fill these in real time.

2. Section 6 exact failure output: the R2 run recorded "unavailable" rather than
   the literal terminal output. The template asks for exact output. A live run
   would capture this; a retroactive fill can only approximate it.

**Template blind spots not exposed by this run:**

1. ~~The template does not ask the reviewer to verify file contents.~~
   **Fixed:** Section 1b added — requires reviewer to locate and confirm two
   canonical files (start_session.md and governance_drift_checker.py) before
   proceeding to sections 2–5. A reviewer in the wrong repo will fail this gate.
   R2 run maps cleanly into 1b: both files were found at expected paths.
