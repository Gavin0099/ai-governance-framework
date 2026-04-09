# No-Python Onboarding Evidence — 2026-03-31

> 類型：內部模擬 artifact
> 說明：此機器平常可用 Python，但本次在受限 shell 中刻意讓 `python`、`python3`、`py` 暫時不在 PATH 上，以驗證 Route B。

---

## 1. 環境記錄

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

## 1b. Repo identity 檢查

```text
File 1：onboarding entrypoint
  Relative path as seen during run: README.md
  Confirmed it exists: Y
  First heading: ai-governance-framework

File 2：drift checker
  Relative path as seen during run: governance_tools/governance_drift_checker.py
  Confirmed it exists: Y
  Opening description: checks governance baseline drift, freshness, contract completeness, and memory schema state
```

---

## 2. Entrypoint 驗證

```text
What does this framework do, in one sentence?
  It provides a repo-local governance runtime that constrains AI-assisted engineering work through contracts, rule packs, checks, and reviewer-visible artifacts.

What file does README.md say to open first for onboarding?
  start_session.md

Did you find that file?  Y
If N, where did you look and what did you find instead?
  N/A
```

---

## 3. Adoption path 驗證

```text
What is the canonical adoption command?
  python governance_tools/adopt_governance.py --target <repo>

What tool does it use? (name the script, not just "python")
  governance_tools/adopt_governance.py

What does adoption produce in the target repo? (name at least one file or artifact)
  .governance/baseline.yaml, contract.yaml, governance markdown pack, memory scaffold

Is there a fallback adoption path if Python is unavailable?  N
If Y, what is it and what does it require?
  N/A
```

---

## 4. Minimum session flow 驗證

```text
List the steps of the minimum governance session flow in order:
1. Load repo-local governance entry docs and contract
2. Run pre-task checks / classify task
3. Execute task under rule pack / evidence discipline
4. Run session closeout and review artifacts

Which step requires execution to verify?
  Drift / runtime tooling execution begins at step 2.

Which steps can be verified by reading only?
  Steps 1 and the documented outline of 3–4.
```

---

## 5. Drift check 驗證

```text
What command checks for governance drift?
  python governance_tools/governance_drift_checker.py --repo . --framework-root .

What does it check? (describe in one sentence — not the command, the behavior)
  It checks baseline drift, contract completeness, plan freshness, protected files, and memory schema state.

Where is that tool located in the repo?
  governance_tools/governance_drift_checker.py
```

---

## 6. Blocker 記錄

```text
At what step did execution become required to continue?
  When adoption or drift tools needed Python to run.

Exact command that failed:
  python governance_tools/adopt_governance.py --target <repo>

Exact failure output (or "command not found"):
  'python' is not recognized as an internal or external command, operable program or batch file.

Was there a documented recovery path for this failure?  N
If Y, what was it?
  N/A
If N, where in the docs did the path end?
  The docs described the canonical Python-based path but did not provide a non-Python fallback adoption route.
```

---

## 7. Onboarding verdict

```text
Task 1：understand what this is for:         Y
Task 2：understand how adoption works:       Y
Task 3：describe minimum session flow:       Partial
Task 4：find the drift checker:              Y

Recommended next step to unblock execution:
  Provide a documented non-Python fallback or a packaged bootstrap lane for adopters who cannot run Python locally.
```

---

## 結論

這份 artifact 證明：即使在沒有 Python 的情境下，reviewer 仍能理解 framework 的定位、adoption 入口與 drift checker 位置；但真正執行 adoption / drift 時仍會卡在 Python 依賴，且當時尚無正式 fallback 路徑。
