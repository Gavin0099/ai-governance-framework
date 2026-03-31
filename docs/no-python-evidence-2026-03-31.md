# No-Python Onboarding Evidence

> Internal simulation artifact on a machine that normally has Python available.
> Route B was exercised inside a constrained shell where `python`, `python3`, and `py` were intentionally made unavailable on PATH for the duration of the test.

---

## 1. Environment record

```text
Date: 2026-03-31
Operating system: Windows
Shell / terminal used: PowerShell (constrained PATH sandbox)

Commands attempted (copy exact output or "command not found"):
  python --version: 'python' is not recognized as an internal or external command, operable program or batch file.
  python3 --version: 'python3' is not recognized as an internal or external command, operable program or batch file.
  py --version: No installed Python found!
```

---

## 1b. Repo identity check

```text
File 1 — onboarding entrypoint:
  Relative path as you see it (e.g. start_session.md or docs/start_session.md): start_session.md
  Confirmed it exists (Y / N / cannot find): Y
  First heading or first sentence of the file: # Start Session

File 2 — drift checker:
  Relative path as you see it: governance_tools/governance_drift_checker.py
  Confirmed it exists (Y / N / cannot find): Y
  What does the first --help line or opening docstring say it does? Check whether a repo's governance files have drifted from the recorded baseline.
```

---

## 2. Entrypoint verification

```text
What does this framework do, in one sentence?
It provides an executable governance layer around AI-assisted engineering sessions so adoption, session boundaries, drift, and review evidence can be checked instead of left to prompts alone.

What file does README.md say to open first for onboarding?
start_session.md

Did you find that file?  Y / N
Y
If N, where did you look and what did you find instead?
N/A
```

---

## 3. Adoption path verification

```text
What is the canonical adoption command?
python governance_tools/adopt_governance.py --target /path/to/your/repo

What tool does it use? (name the script, not just "python")
governance_tools/adopt_governance.py

What does adoption produce in the target repo? (name at least one file or artifact)
It creates or refreshes governance baseline artifacts such as .governance/baseline.yaml, and may create missing AGENTS.md / contract.yaml / PLAN.md templates.

Is there a fallback adoption path if Python is unavailable?  Y / N
Y
If Y, what is it and what does it require?
bash scripts/init-governance.sh --target /path/to/your/repo --adopt-existing ; it requires bash and is documented as Linux/macOS-only fallback when Python is unavailable.
```

---

## 4. Minimum session flow verification

```text
List the steps of the minimum governance session flow in order:
1. Confirm the tools are available with contract_validator --help
2. Run a minimal pre_task_check governance check
3. Run a domain-aware session_start against an example contract
4. Optionally run the demo app or inspect the next recommended files

Which step requires execution to verify?
Steps 1 through 3 require execution to verify as runnable behavior.

Which steps can be verified by reading only?
The conceptual sequence, command locations, and expected purpose of each step can be verified by reading start_session.md without execution.
```

---

## 5. Drift check verification

```text
What command checks for governance drift?
python governance_tools/governance_drift_checker.py --repo /path/to/your/repo --framework-root .

What does it check? (describe in one sentence — not the command, the behavior)
It checks whether the repo's governance baseline, protected files, freshness state, contract shape, and related recorded expectations have drifted from the framework's baseline.

Where is that tool located in the repo?
governance_tools/governance_drift_checker.py
```

---

## 6. Blocker record

```text
At what step did execution become required to continue?
At the Prerequisites section of start_session.md, when the documented environment check had to be run before continuing on Route A.

Exact command that failed:
python --version

Exact failure output (or "command not found"):
'python' is not recognized as an internal or external command, operable program or batch file.

Was there a documented recovery path for this failure?  Y / N
Y
If Y, what was it?
Try python3 and py first; if all three fail, stop and follow Route B in start_session.md by filling docs/no-python-onboarding-evidence.md and saving it as docs/no-python-evidence-<YYYY-MM-DD>.md.
If N, where in the docs did the path end?
N/A
```

---

## 7. Onboarding verdict

```text
Task 1 — understand what this is for:         Y
Task 2 — understand how adoption works:       Y
Task 3 — describe minimum session flow:       Y
Task 4 — find the drift checker:              Y

Recommended next step to unblock execution:
Run the same Route B procedure in a genuinely Python-unavailable environment with an independent reviewer, then compare the resulting artifact against docs/beta-gate/onboarding-pass-criteria.md.
```

---

## Artifact validity

This completed copy fills all seven sections, records the exact failure output, and gives a concrete next step beyond "install Python".

It is suitable as an internal Route B simulation artifact.
It should not be treated as independent-reviewer gate evidence without a genuinely constrained external run.
