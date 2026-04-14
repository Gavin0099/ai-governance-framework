# Adoption Test Report — cli (GLUpdateTool)
<!-- governance-test-artifact: adoption-validation -->
<!-- repo: cli (GL Hub Firmware Update CLI) -->
<!-- created: 2026-04-14 -->
<!-- author: GitHub Copilot (Claude Sonnet 4.6, Tier B) -->

## 目的

驗證 `ai-governance-framework` 在 **完全未導入 governance 的 C++ CLI repo** 上的
首次 adopt 流程，並確認 C++ GTest 情境下的 test artifact 策略。

此次測試的三個核心問題：

1. **Green-field adoption** — `adopt_governance.py` 首次建立 scaffold，沒有現有 baseline ✅
2. **C++ GTest + CMake** — test artifact 不是 pytest JSON，而是 CI pipeline 輸出的 GTest XML；
   本地無法直接 `pytest` → `skip_test_result_check` 的適用性判斷 ✅ **Scenario A 確認**
3. **framework submodule 不存在** — 需以 `--framework-root` 指向 framework repo ✅

---

## Repo 現狀（測試前已知）

| 項目 | 狀態 |
|------|------|
| Path | `e:\BackUp\Git_EE\cli` |
| Active branch | `main` |
| Language | C++ (CMake, cross-platform: Windows/Linux/macOS) |
| Purpose | USB Hub firmware update CLI (GL ISP tool, command line variant) |
| Tests | `TestSuite/UTest/`（GTest framework，wmain/main entrypoint）|
| CI | GitLab CI pipeline — Build / Lint / TestUnit / Audit stages |
| Test CI artifact path | `./Build/*/Report/` (GTest XML via `DevOps.ps1 Test`)  |
| framework submodule | **不存在**（只有 `SubModule/IspEngine_Lib`）|
| governance/ | **不存在** |
| .governance/ | **不存在** |
| contract.yaml | **不存在** |
| AGENTS.md | **不存在** |
| memory/ | **不存在** |
| .governance/baseline.yaml | **不存在** |
| artifacts/ | **不存在** |
| governance/gate_policy.yaml | **不存在** |

---

## 前置設定

```powershell
# framework venv 啟動（使用 ai-governance-framework 的 venv）
cd e:\BackUp\Git_EE\ai-governance-framework
.venv\Scripts\Activate.ps1

# pyyaml 安裝（venv 中未預裝，gate_policy YAML 解析需要）
pip install pyyaml   # → pyyaml-6.0.3 installed

cd e:\BackUp\Git_EE\cli
```

> ⚠️ **重要發現**：framework venv 未安裝 `pyyaml`，導致 `gate_policy.yaml` YAML 解析失敗，
> `_HAS_YAML=False`，policy_source 落回 `builtin_default`（fail_mode=strict, blocked=True）。
> 安裝後問題解決：`policy_source=repo_local`, `gate.blocked=False`。
> **已修正：`pyyaml>=6.0` 加入 framework requirements.txt（commit 同批）。**

---

## T1：Readiness 掃描（導入前）

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\external_repo_readiness.py `
  --repo . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework `
  --format human
```

**實際輸出摘要：**
```
ready              = False
git_repo_present   = True
governance_baseline_present = False
project_facts_present       = False
memory_schema_status        = missing
framework_source_canonical  = False
contract_resolved           = False
[governance_drift] severity = critical
  [critical] baseline_yaml_present: .governance/baseline.yaml not found
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| 整體 readiness status | `ready=False`，severity=critical | PASS（符合預期）|
| memory_schema_status | `missing` | PASS（符合預期）|
| framework_source | `framework_source_canonical=False`（使用 --framework-root）| PASS（符合預期）|
| contract.yaml detected | `contract_resolved=False` | PASS（符合預期：absent）|

---

## T2：首次 Adopt Governance

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\adopt_governance.py `
  --target . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework
```

**實際輸出：**
```
Adopting governance baseline into existing repo: E:\BackUp\Git_EE\cli
Baseline source: E:\BackUp\Git_EE\ai-governance-framework\baselines\repo-min

[adopt_governance]
ok=True | severity=ok | checks=18/18
  PASS: …全部 18 項…

Wrote .governance-payload-config.yaml (repo_type=firmware)
```

**建立的檔案：**
- `.governance/baseline.yaml` ✅
- `AGENTS.base.md`, `AGENTS.md` ✅
- `contract.yaml`（skeleton）✅
- `PLAN.md` ✅
- `memory/01–04` ✅
- `governance/AGENT.md`, `ARCHITECTURE.md`, `AUTHORITY.md`, `HUMAN-OVERSIGHT.md`, `NATIVE-INTEROP.md`, `REVIEW_CRITERIA.md`, `RULE_REGISTRY.md`, `SYSTEM_PROMPT.md`, `TESTING.md` ✅
- `governance/rules/`（cpp, common, refactor, kernel-driver, gl-hub-vendor-cmd 等，19 files）✅
- `.github/workflows/governance-drift.yml` ✅

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| adopt 無錯誤完成 | `ok=True`, 18/18 PASS | PASS |
| .governance/baseline.yaml 建立 | PASS | PASS |
| contract.yaml 建立 | copied from template | PASS |
| memory/ 初始化 01–04 | 四個 scaffold 均建立 | PASS |
| governance/rules/ 建立 | 19 個 rule pack 檔案 | PASS |
| 需要手動補充的欄位 | `name`, `domain`, `source_roots`, `language_hint`, `test_framework` | WARN（已補充，見 T3）|

---

## T3：Contract.yaml 補充（C++ CLI domain）

```yaml
name: gl-hub-update-cli-contract
domain: firmware-update-cli
rule_roots:
  - governance/rules
source_roots:
  - Source/
  - TestSuite/
language_hint: cpp
test_framework: gtest
```

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\runtime_hooks\core\pre_task_check.py `
  --contract .\contract.yaml `
  --risk L1 `
  --task-text "Add new ISP command for hub model XY"
```

**實際輸出：**
```
ok=True  freshness=FRESH  rules=common
contract=firmware-update-cli/medium
suggested_rules_preview=common,firmware-update-cli,objective-c,cpp,python
suggested_skills=code-style,governance-runtime,python
suggested_agent=python-agent
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| contract.yaml 語法合法 | YAML 解析正常，無 placeholder | PASS |
| pre_task_check 無錯誤 | `ok=True`, exit 0 | PASS |
| domain 被識別 | `contract=firmware-update-cli` | PASS |
| task_level response | `contract_risk_tier=medium` | PASS |

---

## T4：首次 Session End Hook（zero history, no gate_policy）

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_end_hook.py `
  --project-root .
```

**實際輸出：**
```
ok=False  closeout_status=closeout_missing
policy_source=builtin_default  fallback_used=True  repo_policy_present=False
fail_mode=strict  artifact_state=absent  blocked=True
[ADVISORY] test_result_artifact_absent
canonical_audit_trend: entries_read=1/20  signal_ratio=100%  adoption_risk=True
warning: [gate_policy] repo_local_policy_missing
error: [gate_policy:strict] test-result artifact absent
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | `builtin_default`（repo_local_policy_missing）| PASS |
| repo_local_policy_missing | warning 觸發 | PASS |
| test_result_artifact_absent | advisory 觸發 | PASS |
| 其他 signals | `closeout_file_missing` | WARN（預期行為）|
| gate.blocked | `True`（strict + no artifact）| PASS |
| audit_log entry created | `entries_read=1/20` | PASS |

---

## T5：Test Artifact 策略判斷（C++ GTest 特殊路徑）

### 5a. 本地建置評估

```powershell
cmake --version   # → CommandNotFoundException（cmake 不在 PATH）
Get-ChildItem Build -Recurse -ErrorAction SilentlyContinue   # → Build/ 不存在
```

### 5c. 判決

- `cmake` 不在 PATH（系統未安裝或環境未配置）
- `Build/` 目錄不存在（無預建 binary）
- 建置需要 GitLab CI Docker 環境（VS2019 + WDK）

→ **Scenario A（CI-only build）** 確認。

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| cmake 可用 | `CommandNotFoundException` | PASS（CI-only 確認）|
| 本地 Build/ 有 binary | Build/ 不存在 | PASS（CI-only 確認）|
| GTest XML 可生成方式 | CI-only（Docker VS2019 + `DevOps.ps1 Test`）| PASS |
| 選擇情境 | **A**（CI-only，本地無法建置）| PASS |

---

## T6：Gate Policy 配置

**情境 A gate_policy.yaml：**

```yaml
version: "1"

fail_mode: audit

skip_test_result_check: true   # C++ GTest: build requires CI Docker environment (VS2019)
                                # Local cmake not available; Build/ directory absent
                                # Scenario A confirmed — local test execution not feasible
                                # Target: wire CI GTest XML to artifacts/ in future
                                # CI artifact path: ./Build/*/Report/ via DevOps.ps1 Test

blocking_actions:
  - production_fix_required

unknown_treatment:
  mode: never_block

artifact_stale_seconds: 0

# hook_coverage_tier: B   # GitHub Copilot in VS Code — manual task trigger
```

> ⚠️ **修復點**：`pyyaml` 未安裝時 `_HAS_YAML=False`，gate_policy.yaml 無法解析，
> 落回 `builtin_default`（fail_mode=strict）。安裝後 `policy_source=repo_local`，
> `fail_mode=audit`，`blocked=False`。

**第二次 session_end_hook 輸出（安裝 pyyaml 後）：**
```
ok=False  closeout_status=closeout_missing
policy_source=repo_local  fallback_used=False  repo_policy_present=True
fail_mode=audit  artifact_state=absent  blocked=False
[skipped] test_result_check: structural absence declared
canonical_audit_trend: entries_read=3/20  signal_ratio=67%  adoption_risk=True
```

> `ok=False` 仍存在，原因是 `closeout_file_missing`（session-closeout.txt 未寫入）。
> gate 未阻擋，為預期行為。

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | `repo_local` | PASS |
| signals after gate_policy | `[skipped] test_result_check: structural absence declared` | PASS |
| gate.blocked | `False` | PASS |
| 選擇情境 | **A**（skip_test_result_check: true）| PASS |

---

## T7：Hook Coverage Tier 宣告

```yaml
# hook_coverage_tier: B   # GitHub Copilot in VS Code — manual task trigger
```

| Check | Actual |
|-------|--------|
| 日常使用 agent | GitHub Copilot（VS Code Copilot Chat）|
| hook_coverage_tier declared | **B**（VS Code task 手動觸發）|

---

## T8：Drift Checker（首次 baseline 建立後）

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\governance_drift_checker.py `
  --repo . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework
```

**實際輸出：**
```
ok=True  severity=ok  checks=18/18
  PASS: 全部 18 項（agents_sections_filled, baseline_yaml_freshness,
        framework_version_current, memory_schema_complete … 等）
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| critical drift | `severity=ok`，0 critical | PASS |
| framework_source status | `framework_version_current=PASS`（1.0.0 == 1.0.0）| PASS |
| memory_schema_status | `memory_schema_complete=PASS` | PASS |

---

## T9：Commit Governance Scaffold

```powershell
git add governance/ .governance/ contract.yaml AGENTS.base.md AGENTS.md PLAN.md memory/ `
        artifacts/.gitkeep .gitignore .governance-payload-config.yaml .github/
git commit -m "chore: adopt ai-governance-framework scaffold (green-field, C++ CLI)"
# main 是 protected branch → feature branch
git checkout -b feature/adopt-ai-governance-framework
git push -u origin feature/adopt-ai-governance-framework
```

**.gitignore 新增：**
```gitignore
artifacts/runtime/
artifacts/test_result.json
artifacts/test_result.xml
artifacts/session-closeout.txt
```

| Check | Actual |
|-------|--------|
| commit 前 staging area 合理 | 42 files: governance scaffold + memory + .gitignore + .github workflow |
| .gitignore 更新 | ✅ 4 個 governance runtime artifact 排除規則 |
| committed | ✅ `7a7a7cc`（rebased on top of `10fd268`）|
| pushed | ✅ `feature/adopt-ai-governance-framework` → remote |

---

## 觀察重點（三 repo 比較）

| 觀察點 | KDC（Tier A, C++, kernel driver）| Bookstore-Scraper（Tier B, Python）| cli（Tier B, C++, user-space CLI）|
|--------|------|------|------|
| governance 導入狀態（測試前）| 已導入 + gate_policy | 已導入，無 gate_policy | **完全未導入** |
| test artifact 策略 | skip（WDK/CI-only）| pytest-json-report（情境 A）| **CI GTest XML（Scenario A, skip）** |
| framework 連接方式 | submodule | submodule（.ai-governance-framework）| **外部 --framework-root** |
| 首次 signal_ratio | 0%（第一次）| 100% → 50%（window dilution）| 100% → 67%（3 entries）|
| build environment | WDK + VS | pip install | CMake + VS2019 Docker |
| pre_task_check domain rules | firmware-kernel | bookstore-scraper | firmware-update-cli |
| pyyaml 陷阱 | — | — | **venv 未預裝 → gate_policy 解析失敗** |

---

## 非預期行為 / Blockers

| 問題 | 描述 | 解法 |
|------|------|------|
| `pyyaml` 未安裝在 venv | `_HAS_YAML=False` → gate_policy YAML 解析失敗 → `policy_source=builtin_default`，`fail_mode=strict`，`blocked=True` | `pip install pyyaml`；**已修正：加入 requirements.txt** |
| `main` 是 protected branch | `git push` 被 GitLab 拒絕 | 改用 `feature/adopt-ai-governance-framework` branch |
| `ok=False` 持續存在 | `closeout_file_missing`：session-closeout.txt 未寫入 | 預期行為；gate 未阻擋（blocked=False），完整 closeout 需日常工作流程 |

---

## 整體通過門檻

| 測試 | 結果 |
|------|------|
| T1: Readiness 掃描 | ✅ PASS — 全部 missing 符合預期 |
| T2: Adopt Governance | ✅ PASS — 18/18 ok |
| T3: Contract.yaml + pre_task_check | ✅ PASS — domain=firmware-update-cli |
| T4: 首次 Session End Hook | ✅ PASS — gate.blocked=True（預期），advisory 觸發 |
| T5: Test Artifact 策略判斷 | ✅ PASS — Scenario A 確認 |
| T6: Gate Policy 配置 | ✅ PASS — policy_source=repo_local，gate.blocked=False |
| T7: Hook Coverage Tier 宣告 | ✅ PASS — Tier B，GitHub Copilot |
| T8: Drift Checker | ✅ PASS — severity=ok，18/18，drift=none |
| T9: Commit Governance Scaffold | ✅ PASS — 42 files committed，feature branch pushed |

**整體評分：9 / 9 tests PASS** ✅

---

## Agent 執行備註

- 測試 agent 名稱：**GitHub Copilot**（Claude Sonnet 4.6, Tier B）
- 測試日期：2026-04-14
- 測試環境：Windows PowerShell + framework venv `e:\BackUp\Git_EE\ai-governance-framework\.venv`
- framework-root：`e:\BackUp\Git_EE\ai-governance-framework`（無 submodule，外部指向）
- 本次執行者 hook coverage tier：**B**（VS Code 手動觸發）
- 備注：
  1. `pyyaml` 需手動安裝到 framework venv；不安裝會導致 gate_policy 解析靜默失敗，
     症狀為 `blocked=True` 即使 `gate_policy.yaml` 存在。已修正：加入 `requirements.txt`。
  2. GitLab main branch 是 protected branch，需透過 feature branch + MR 流程合入。
  3. `session_end_hook` `ok=False` 在本 adoption test 情境下屬預期行為（`closeout_file_missing`）；
     gate 評估本身 `blocked=False` 符合通過標準。
