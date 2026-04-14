# Adoption Test Report — cli (GLUpdateTool)
<!-- governance-test-artifact: adoption-validation -->
<!-- repo: cli (GL Hub Firmware Update CLI) -->
<!-- created: 2026-04-14 -->
<!-- author: test agent (fill in agent name + tier) -->

## 目的

驗證 `ai-governance-framework` 在 **完全未導入 governance 的 C++ CLI repo** 上的
首次 adopt 流程，並確認 C++ GTest 情境下的 test artifact 策略。

此次測試的三個核心問題：

1. **Green-field adoption** — `adopt_governance.py` 首次建立 scaffold，沒有現有 baseline
2. **C++ GTest + CMake** — test artifact 不是 pytest JSON，而是 CI pipeline 輸出的 GTest XML；
   本地無法直接 `pytest` → `skip_test_result_check` 的適用性判斷（與 Bookstore-Scraper 的邏輯不同）
3. **framework submodule 不存在** — 需以 `--framework-root` 指向 framework repo

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

cd e:\BackUp\Git_EE\cli
```

---

## T1：Readiness 掃描（導入前）

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\external_repo_readiness.py `
  --repo . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework `
  --format human
```

**預期：**
- 大量 missing：無 contract.yaml、無 memory、無 baseline
- `memory_schema_status: missing`
- `framework_source: not_present`

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| 整體 readiness status | （填入）| |
| memory_schema_status | （填入：預期 missing）| |
| framework_source | （填入：預期 not_present）| |
| contract.yaml detected | （填入：預期 absent）| |

---

## T2：首次 Adopt Governance

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\adopt_governance.py `
  --target . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework
```

**預期建立的檔案：**
- `.governance/baseline.yaml`
- `AGENTS.base.md`
- `contract.yaml`（skeleton）
- `PLAN.md`
- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `governance/*.md`（AGENT.md, ARCHITECTURE.md, TESTING.md 等）
- `governance/rules/`

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| adopt 無錯誤完成 | （填入）| |
| .governance/baseline.yaml 建立 | （填入）| |
| contract.yaml 建立 | （填入）| |
| memory/ 初始化 01–04 | （填入）| |
| governance/rules/ 建立 | （填入）| |
| 需要手動補充的欄位 | （填入：contract domain 等）| |

---

## T3：Contract.yaml 補充（C++ CLI domain）

`adopt_governance.py` 建立的 `contract.yaml` 是 skeleton，需補充 C++ 相關欄位：

```yaml
# 補充這些欄位
name: gl-hub-update-cli-contract
domain: firmware-update-cli
rule_roots:
  - governance/rules
# language hints（如果 adopt 沒有自動推斷）
# 可補：
#   - Source/        (main C++ source)
#   - TestSuite/     (GTest)
```

執行後確認 pre_task_check 可讀取 contract：

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\runtime_hooks\core\pre_task_check.py `
  --contract .\contract.yaml `
  --task-level L1 `
  --task-text "Add new ISP command for hub model XY"
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| contract.yaml 語法合法 | （填入）| |
| pre_task_check 無錯誤 | （填入）| |
| domain 被識別 | （填入）| |
| task_level response | （填入）| |

---

## T4：首次 Session End Hook（zero history, no gate_policy）

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_end_hook.py `
  --repo . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework
```

**預期行為：**
- `repo_local_policy_missing` → fallback strict
- `test_result_artifact_absent` advisory **應觸發**（artifacts/ 不存在或空）
- `canonical_audit_log` 建立第一筆記錄
- `gate.blocked = True`（strict + advisory）

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | （填入：預期 fallback_default）| |
| repo_local_policy_missing | （填入）| |
| test_result_artifact_absent | （填入：預期 PRESENT）| |
| 其他 signals | （填入）| |
| gate.blocked | （填入）| |
| audit_log entry created | （填入）| |

---

## T5：Test Artifact 策略判斷（C++ GTest 特殊路徑）

**背景：** 這是 C++ GTest repo，與 Bookstore-Scraper（Python pytest）的邏輯不同：

| 情境 | 說明 | 正確處置 |
|------|------|----------|
| A | 測試只能在 CI（Docker + VS2019）跑，本地無法建置 | `skip_test_result_check: true`（合法的結構性宣告）|
| B | 本地可建置但 GTest XML 輸出路徑不對 | 建置後複製 XML 到 `artifacts/test_result.xml` |
| C | 本地可直接跑預建的 binary | `artifacts/test_result.xml` 可生成 |

### 5a. 嘗試本地建置評估

```powershell
# 確認 CMake 是否可用
cmake --version

# 查看是否有預建的 binary
Get-ChildItem Build -Recurse -ErrorAction SilentlyContinue -Filter "*.exe" | Select-Object FullName | Select-Object -First 5
```

### 5b. 嘗試取得 GTest XML（如果 binary 存在）

```powershell
# 如果有預建 GTest binary（路徑依實際 Build 輸出調整）
# Build\<config>\UTest.exe --gtest_output=xml:artifacts/test_result.xml
```

### 5c. 判決

依照上述結果，在 T6 中選擇正確的 gate_policy 配置：
- **CI-only build** → 情境 A → `skip_test_result_check: true`（同 KDC Pattern）
- **本地可生成 XML** → 情境 B/C → 建立 artifact 後不用 skip

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| cmake 可用 | （填入）| |
| 本地 Build/ 有 binary | （填入）| |
| GTest XML 可生成方式 | （填入：CI-only / 本地建置 / 預建 binary）| |
| 選擇情境 | （填入：A / B / C）| |

---

## T6：Gate Policy 配置

根據 T5 判斷，建立 `governance/gate_policy.yaml`：

### 情境 A（CI-only，本地無法建置）
```yaml
version: "1"

fail_mode: audit

skip_test_result_check: true   # C++ GTest: build requires CI Docker environment
                                # Local test execution is not feasible
                                # Target: wire CI GTest XML to artifacts/ in future

blocking_actions:
  - production_fix_required

unknown_treatment:
  mode: never_block

artifact_stale_seconds: 0
```

### 情境 B/C（本地可生成 GTest XML）
```yaml
version: "1"

fail_mode: audit

blocking_actions:
  - production_fix_required

unknown_treatment:
  mode: block_if_count_exceeds
  threshold: 3

artifact_stale_seconds: 86400
# DO NOT use skip_test_result_check (GTest XML can be generated locally)
```

**寫入後執行第二次 hook：**
```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_end_hook.py `
  --repo . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | （填入：預期 repo_local）| |
| signals after gate_policy | （填入）| |
| gate.blocked | （填入：預期 False）| |
| 選擇情境 | （填入：A / B / C）| |

---

## T7：Hook Coverage Tier 宣告

CLI repo 的日常 agent 決定 tier：

- **Claude Code** → `hook_coverage_tier: A`（Stop hook 自動觸發）
- **GitHub Copilot** → `hook_coverage_tier: B`（VS Code task 手動觸發）

在 `governance/gate_policy.yaml` 加入 comment 區塊：

```yaml
# ── hook coverage tier ─────────────────────────────────────────────────────
# Declares the session_end_hook triggering mechanism for this repo.
# Tier A: native auto-closeout (Claude Code Stop hook)
# Tier B: wrapper-based (Copilot VS Code task, Gemini CLI wrapper)
# Tier C: manual only
#
# hook_coverage_tier: A   # <-- 填入正確值
```

| Check | Actual |
|-------|--------|
| 日常使用 agent | （填入）|
| hook_coverage_tier declared | （填入）|

---

## T8：Drift Checker（首次 baseline 建立後）

```powershell
python e:\BackUp\Git_EE\ai-governance-framework\governance_tools\governance_drift_checker.py `
  --repo . `
  --framework-root e:\BackUp\Git_EE\ai-governance-framework
```

**預期：**
- baseline.yaml 剛建立 → drift 應為 none 或 minimal
- 但 framework_source 狀態：使用 `--framework-root`（外部指向），不是 submodule → 確認 checker 如何回報

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| critical drift | （填入：預期 none）| |
| framework_source status | （填入：外部 path vs submodule 行為差異）| |
| memory_schema_status | （填入：預期 complete 或 partial）| |

---

## T9：Commit Governance Scaffold

```powershell
git add governance/ .governance/ contract.yaml AGENTS.base.md PLAN.md memory/ artifacts/.gitkeep
git status
# 確認 .gitignore 是否需要補充（artifacts/runtime/ 等）
```

**需確認 .gitignore 策略：**

```gitignore
# 建議加入（與 KDC / hp-oci 一致）
artifacts/runtime/
artifacts/test_result.json
artifacts/test_result.xml
```

| Check | Actual |
|-------|--------|
| commit 前 staging area 合理 | （填入）|
| .gitignore 更新 | （填入）|
| committed | （填入）|

---

## 觀察重點（三 repo 比較）

| 觀察點 | KDC（Tier A, C++, kernel driver）| Bookstore-Scraper（Tier A, Python）| cli（Tier ?, C++, user-space CLI）|
|--------|------|------|------|
| governance 導入狀態（測試前）| 已導入 + gate_policy | 已導入，無 gate_policy | **完全未導入** |
| test artifact 策略 | skip（WDK/CI-only）| pytest-json-report | CI GTest XML（判斷中）|
| framework 連接方式 | submodule | submodule（.ai-governance-framework）| **外部 --framework-root** |
| 首次 signal_ratio | 0%（第一次）| （待填入）| （待填入）|
| build environment | WDK + VS | pip install | CMake + VS2019 Docker |
| pre_task_check domain rules | firmware-kernel | bookstore-scraper | firmware-update-cli |

---

## 整體通過門檻

全部 9 項測試均需有合理的 PASS / 有說明的 WARN，且：

- adopt 無錯誤（T2）
- `gate.blocked = False`（T6 完成後）
- `policy_source: repo_local`（T6）
- `hook_coverage_tier` 已宣告（T7）
- test artifact 策略已釐清（T5/T6）
- drift = none（T8）

整體評分：**`____ / 9 tests PASS`**（填入）

---

## Agent 執行備註

- 測試 agent 名稱：（填入）
- 測試日期：2026-04-14
- 測試環境：Windows PowerShell + framework venv `e:\BackUp\Git_EE\ai-governance-framework\.venv`
- framework-root：`e:\BackUp\Git_EE\ai-governance-framework`（無 submodule）
- 本次執行者 hook coverage tier：（填入）
- 備注：（填入任何非預期行為或 blockers）
