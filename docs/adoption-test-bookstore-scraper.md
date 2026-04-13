# Adoption Test Report — Bookstore-Scraper
<!-- governance-test-artifact: adoption-validation -->
<!-- repo: bookstore-scraper -->
<!-- created: 2026-04-13 -->
<!-- author: test agent (fill in agent name + tier) -->

## 目的

驗證 `ai-governance-framework` session_end_hook 在 Bookstore-Scraper 上的首次執行行為，
並確認 gate_policy 配置策略。此次測試重點在於：

1. **Python repo + 真實測試** — `test_result_artifact_absent` advisory 的正確處置策略
   （此場景與 hp-oci-avalonia / KDC 不同：不應使用 `skip_test_result_check: true`）
2. **Tier A repo 的首次基準線建立** — 第一次 session_end_hook run 的 signal pattern
3. **pre_task_check 有 domain contract 的情境** — governance/rules 已存在，驗證 hook 實質作用

---

## Repo 現狀（測試前已知）

| 項目 | 狀態 |
|------|------|
| Path | `e:\BackUp\Git_EE\Bookstore-Scraper` |
| Active branch | `feature/team-buy-import-bundle` |
| Language | Python（scraper，bookstore data pipeline）|
| Tests | 7 test files under `tests/`（test_book, test_excel_writer, test_http_client, test_json_image_materialization, test_json_writer, test_scraper_regressions, test_windmill_scraper）|
| Framework submodule | `.ai-governance-framework`（pinned to `5c700a0`）|
| governance/ | domain contract 已存在（rules, AGENT.md, ARCHITECTURE.md, TESTING.md 等）|
| contract.yaml | 存在（domain: bookstore-scraper）|
| AGENTS.md | 存在（repo-specific extension）|
| memory/ | 已初始化（00–04）|
| .governance/baseline.yaml | 存在（adopt 過一次，source_commit = 5c700a0）|
| artifacts/ | 目錄存在但**完全空白** |
| governance/gate_policy.yaml | **不存在**（session_end_hook 會 fallback → `repo_local_policy_missing`）|
| Test result artifact | **不存在**（尚未設定 pytest JSON report）|

---

## 前置設定

```powershell
# framework venv（在 framework repo 啟動）
cd e:\BackUp\Git_EE\ai-governance-framework
.venv\Scripts\Activate.ps1

# 確認 submodule 版本
cd e:\BackUp\Git_EE\Bookstore-Scraper
git submodule status
```

---

## T1：Submodule 版本一致性

**目的：** 確認 `.ai-governance-framework` submodule 釘的 commit 是否已落後於 framework main。

```powershell
cd e:\BackUp\Git_EE\Bookstore-Scraper
git submodule status
# 對照 ai-governance-framework
cd e:\BackUp\Git_EE\ai-governance-framework
git log --oneline -1
```

**預期：** 可能落後（baseline pin = `5c700a0`，framework HEAD = `39a0937`）。
**意義：** 如果落後，drift checker 會報告 framework_source 狀態。

| | 結果 |
|--|------|
| submodule HEAD | （填入） |
| framework current HEAD | （填入） |
| 版本落差 commits | （填入） |
| PASS / WARN | |

---

## T2：Governance Drift + Readiness

```powershell
cd e:\BackUp\Git_EE\Bookstore-Scraper
python .ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root .\.ai-governance-framework
python .ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root .\.ai-governance-framework --format human
```

**預期：**
- drift：`baseline.yaml` 存在，drift 應為 low 或 minor（但 submodule 可能落後）
- readiness：`memory_schema_status` 應為 complete（00–04 全存在）
- framework_source：可能顯示 outdated（submodule 落後）

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| critical drift items | （填入） | |
| memory_schema_status | （填入） | |
| framework_source | （填入） | |
| contract.yaml detected | （填入） | |

---

## T3：Pre-Task Hook（domain contract 有 rules）

```powershell
python .ai-governance-framework\runtime_hooks\core\pre_task_check.py \
  --contract .\contract.yaml \
  --task-level L1 \
  --task-text "Add new bookstore parser and export to Excel"
```

**預期：**
- 應觸發 domain contract rule 過濾
- `decision_boundary`、`boundary_effect` 應有輸出
- rule pack 建議應包含 domain-level rules（bookstore-scraper domain）

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| hook 執行無錯誤 | （填入） | |
| domain rules 被 loaded | （填入） | |
| decision_boundary 存在 | （填入） | |
| task_level response | （填入） | |

---

## T4：首次 Session End Hook（無 gate_policy，無歷史）

```powershell
python .ai-governance-framework\governance_tools\session_end_hook.py \
  --repo . \
  --framework-root .\.ai-governance-framework
```

**預期行為：**
- `repo_local_policy_missing` warning → fallback 使用 framework default（`fail_mode: strict`）
- `test_result_artifact_absent` advisory signal **應觸發**（artifacts/ 空，無 JSON result）
  - ⚠️ 此處與 hp-oci-avalonia / KDC 不同：這是 Python repo，不應用 `skip_test_result_check`
  - 正確處置見 T6
- `canonical_audit_log` 建立第一筆記錄（E8a log entry）
- `signal_ratio` = 0%（第一次執行，window 無歷史）或 100%（如果 signal 計入當前這次）
- `gate.blocked` = 可能為 True（strict + advisory 存在）→ 需用 `fail_mode: audit` 或處置 test artifact

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | （填入：應為 `fallback_default`）| |
| repo_local_policy_missing warning | （填入）| |
| test_result_artifact_absent signal | （填入：應為 PRESENT）| |
| signal list | （填入所有 signals）| |
| gate.blocked | （填入）| |
| canonical_audit_log entry created | （填入）| |

---

## T5：確認 Test Result Artifact 策略

**背景：** Bookstore-Scraper 有真實 Python tests。`test_result_artifact_absent` 的正確處置
不是 `skip_test_result_check: true`（那是 C++ / 結構性無測試的宣告），而是建立 test result artifact 生成管道。

### 5a. 嘗試直接執行測試，看是否能產生 JSON report

```powershell
cd e:\BackUp\Git_EE\Bookstore-Scraper
# 確認 pytest-json-report 是否可用
python -m pytest tests/ --json-report --json-report-file=artifacts/test_result.json -x --tb=short 2>&1 | Select-Object -First 30
```

如果 `pytest-json-report` 未安裝：
```powershell
pip install pytest-json-report
python -m pytest tests/ --json-report --json-report-file=artifacts/test_result.json -x --tb=short 2>&1 | Select-Object -First 30
```

**預期：**
- pytest-json-report 可安裝
- 部分測試可能 pass，部分可能因外部依賴（network / bookstore APIs）失敗
- `artifacts/test_result.json` 被建立

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| pytest-json-report available / installable | （填入）| |
| pytest run exits with code | （填入）| |
| artifacts/test_result.json created | （填入）| |
| test pass/fail counts | （填入）| |

### 5b. 如果 tests 失敗（外部依賴）

記錄原因，確認是**網路依賴型失敗**還是**程式碼 regression**。
此為 `test_result_artifact_absent` vs `test_result_interpretation_risk` 的分岔點。

---

## T6：Gate Policy 配置（根據 T5 結果）

根據 T5 結果，選擇正確的 `governance/gate_policy.yaml` 配置：

### 情境 A：test artifact 可生成（T5 成功）
```yaml
version: "1"
fail_mode: audit
blocking_actions:
  - production_fix_required
unknown_treatment:
  mode: block_if_count_exceeds
  threshold: 3
artifact_stale_seconds: 86400
# DO NOT use skip_test_result_check: true (Python repo with real tests)
```

### 情境 B：test artifact 無法生成（外部依賴導致 pytest 完全無法執行）
```yaml
version: "1"
fail_mode: audit
skip_test_result_check: true   # ONLY if pytest cannot run at all (not just test failures)
# NOTE: This is a temporary declaration. Target: fix pytest setup to generate artifact.
blocking_actions:
  - production_fix_required
unknown_treatment:
  mode: never_block
artifact_stale_seconds: 0
```

**寫入後：**
```powershell
# 建立 gate_policy
# (使用情境 A 或 B 的 YAML 寫入 governance/gate_policy.yaml)

# 再次執行 session_end_hook
python .ai-governance-framework\governance_tools\session_end_hook.py \
  --repo . \
  --framework-root .\.ai-governance-framework
```

**預期（情境 A）：**
- `policy_source: repo_local`
- `test_result_artifact_absent` signal 消失（artifact 已存在）
- `gate.blocked = False`

**預期（情境 B）：**
- `policy_source: repo_local`
- `[skipped] test_result_check: structural absence declared`
- `gate.blocked = False`

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | （填入）| |
| signals after gate_policy | （填入）| |
| gate.blocked | （填入）| |
| 選擇情境 A 或 B | （填入）| |

---

## T7：Hook Coverage Tier 宣告

根據此 repo 的日常 agent，宣告正確的 hook coverage tier：

- **如果日常使用 Claude Code** → `hook_coverage_tier: A`（Stop hook 自動觸發）
- **如果日常使用 GitHub Copilot** → `hook_coverage_tier: B`（需 VS Code task 手動觸發）

在 `governance/gate_policy.yaml` 末尾加入 comment 區塊：

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

## T8：第二次 Session End Hook（有 gate_policy，可能有 test artifact）

```powershell
python .ai-governance-framework\governance_tools\session_end_hook.py \
  --repo . \
  --framework-root .\.ai-governance-framework
```

**預期：**
- `policy_source: repo_local`
- signal 清乾淨（或只剩 non-blocking advisory）
- `gate.blocked = False`
- canonical_audit_log 累積第 2 筆
- `signal_ratio` / `adoption_risk` 有初步 E8b 數值

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | （填入）| |
| signals | （填入）| |
| gate.blocked | （填入）| |
| signal_ratio (E8b) | （填入）| |
| adoption_risk | （填入）| |
| canonical_audit_log entries | （填入）| |

---

## 觀察重點（與 hp-oci-avalonia 比較）

此 repo 的測試結果用於驗證：

| 觀察點 | hp-oci-avalonia（Tier B, C#）| Bookstore-Scraper（Tier A, Python）|
|--------|----------------------------|------------------------------------|
| test_result_artifact | structural absence → skip=true | real tests → 應生成 artifact |
| hook coverage tier | B（Copilot VS Code task）| A（Claude Stop hook）預期 |
| 首次 signal_ratio | 50%（window dilution）| （待填入） |
| gate_policy fallback | strict → blocked | strict → blocked |
| pre_task_check domain | 無 rules（fallback）| 有 rules → 應顯示 rule content |
| E8b trend reliability | variable（Tier B）| high（Tier A）|

---

## 整體通過門檻

全部 8 項測試均需有合理的 PASS / 有說明的 WARN，且：

- `gate.blocked = False`（T8 完成後）
- `policy_source: repo_local`（T6/T8）
- `hook_coverage_tier` 已宣告（T7）
- test artifact 策略已釐清（T5/T6）：情境 A 優先；B 為暫時降級

整體評分：**`____ / 8 tests PASS`**（填入）

---

## Agent 執行備註

- 測試 agent 名稱：（填入，例如：GitHub Copilot / Claude Code / etc.）
- 測試日期：2026-04-13
- 測試環境：Windows PowerShell + framework venv `.venv`
- 本次測試的 hook coverage tier（此次執行者）：（填入）
- 備注：（填入任何非預期行為或 blockers）
