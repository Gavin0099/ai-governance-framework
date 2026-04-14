# Adoption Test Report — Bookstore-Scraper
<!-- governance-test-artifact: adoption-validation -->
<!-- repo: bookstore-scraper -->
<!-- created: 2026-04-13 -->
<!-- author: GitHub Copilot (Claude Sonnet 4.6) / Tier B -->

## 目的

驗證 `ai-governance-framework` session_end_hook 在 Bookstore-Scraper 上的首次執行行為，
並確認 gate_policy 配置策略。此次測試重點在於：

1. **Python repo + 真實測試** — `test_result_artifact_absent` advisory 的正確處置策略
   （此場景與 hp-oci-avalonia / KDC 不同：不應使用 `skip_test_result_check: true`）
2. **Tier B repo 的首次基準線建立** — 第一次 session_end_hook run 的 signal pattern
3. **pre_task_check 有 domain contract 的情境** — governance/rules 已存在，驗證 hook 實質作用

---

## Repo 現狀（測試前已知）

| 項目 | 狀態 |
|------|------|
| Path | `e:\BackUp\Git_EE\Bookstore-Scraper` |
| Active branch | `feature/team-buy-import-bundle` |
| Language | Python（scraper，bookstore data pipeline）|
| Tests | 7 test files under `tests/`（test_book, test_excel_writer, test_http_client, test_json_image_materialization, test_json_writer, test_scraper_regressions, test_windmill_scraper）|
| Framework submodule | `.ai-governance-framework`（更新後 pinned to `3120855`）|
| governance/ | domain contract 已存在（rules, AGENT.md, ARCHITECTURE.md, TESTING.md 等）|
| contract.yaml | 存在（domain: bookstore-scraper）|
| AGENTS.md | 存在（repo-specific extension）|
| memory/ | 已初始化（00–04）|
| .governance/baseline.yaml | 存在（adopt 過一次，source_commit = 8b46ada）|
| artifacts/ | 目錄存在，測試後已建立 `runtime/test-results/latest.json` |
| governance/gate_policy.yaml | 測試後**已建立**（情境 A，fail_mode: audit）|
| Test result artifact | 測試後**已建立**（via pytest + ingestor）|

---

## 前置動作（測試期間執行）

```powershell
# 1. pull framework
cd e:\BackUp\Git_EE\ai-governance-framework
git pull origin main
# HEAD → 3120855

# 2. 更新 submodule（原 pin = 8b46ada，落後 38 commits）
cd e:\BackUp\Git_EE\Bookstore-Scraper
git submodule update --remote .ai-governance-framework
# submodule 更新至 3120855

# 3. 安裝 pytest-json-report
python -m pip install pytest-json-report   # 1.5.0

# 4. 執行 pytest 產生 text output
python -m pytest tests/ --tb=short | Out-File pytest_output.txt -Encoding utf8
# 結果：17 failed, 56 passed

# 5. ingest test result
python test_result_ingestor.py --file pytest_output.txt --kind pytest-text --out latest.json

# 6. 建立 governance/gate_policy.yaml（情境 A）
```

---

## T1：Submodule 版本一致性

| | 結果 |
|--|------|
| submodule HEAD（更新前）| `8b46ada` |
| submodule HEAD（更新後）| `3120855` |
| framework current HEAD | `3120855` |
| 版本落差 commits | 38（已同步）|
| PASS / WARN | ⚠️ WARN → 修正後 PASS |

> 原 baseline pin `8b46ada` 落後 framework HEAD 38 commits（含 E9a skip_test_result_check、hook coverage tier 文件等）。
> 已執行 `git submodule update --remote` 補齊。

---

## T2：Governance Drift + Readiness

```powershell
cd e:\BackUp\Git_EE\Bookstore-Scraper
python .ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root .\.ai-governance-framework
python .ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root .\.ai-governance-framework --format human
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| critical drift items | 0（severity=ok，18/18 items PASS）| PASS |
| memory_schema_status | complete（00–04 全存在）| PASS |
| framework_source | framework_version_current=True（adopted=1.1.0, current=1.1.0）| PASS |
| contract.yaml detected | domain=bookstore-scraper, rule_roots=1, documents=4 | PASS |
| ready | True | PASS |

---

## T3：Pre-Task Hook（domain contract 有 rules）

```powershell
python .ai-governance-framework\runtime_hooks\core\pre_task_check.py `
  --contract .\contract.yaml `
  --risk L1 `
  --task-text "Add new bookstore parser and export to Excel"
```

> ⚠️ 正確參數為 `--risk`，不是 `--task-level`（已於本次測試確認，所有文件已更新）。

**實際輸出：**

```
ok=True  freshness=FRESH  rules=common
suggested_rules_preview=common,bookstore-scraper,csharp,python
suggested_skills=code-style,governance-runtime,python
suggested_agent=python-agent
contract_source=explicit  contract=bookstore-scraper  contract_risk_tier=unknown
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| hook 執行無錯誤 | ok=True, exit 0 | PASS |
| domain rules 被 loaded | suggested_rules_preview 含 bookstore-scraper | PASS |
| decision_boundary 存在 | contract=bookstore-scraper, contract_resolved | PASS |
| task_level response | freshness=FRESH, suggested_agent=python-agent | PASS |

---

## T4：首次 Session End Hook（無 gate_policy，無歷史）

```powershell
python .ai-governance-framework\governance_tools\session_end_hook.py `
  --project-root .
```

> ⚠️ `session_end_hook.py` 只接受 `--project-root`，無 `--repo` / `--framework-root` 參數（已確認）。

**實際輸出：**

```
ok=False  closeout_status=closeout_missing
policy_source=framework_default  fallback_used=True  repo_policy_present=False
fail_mode=strict  artifact_state=absent  blocked=True
[ADVISORY] test_result_artifact_absent
signal_ratio=100%  adoption_risk=True
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | framework_default（fallback_used=True）| PASS |
| repo_local_policy_missing warning | 存在 | PASS |
| test_result_artifact_absent signal | PRESENT | PASS |
| signal list | closeout_file_missing, test_result_artifact_absent, adoption_risk | PASS |
| gate.blocked | True（strict + no artifact）| PASS |
| canonical_audit_log entry created | entries_read=1/20, signal_ratio=100% | PASS |

---

## T5：確認 Test Result Artifact 策略

### 5a. 執行 pytest

```powershell
python -m pip install pytest-json-report
python -m pytest tests/ --tb=short | Out-File pytest_output.txt -Encoding utf8
python test_result_ingestor.py --file pytest_output.txt --kind pytest-text --out latest.json
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| pytest-json-report available | 安裝成功（1.5.0）| PASS |
| pytest run exits with code | 1（17 failed, 56 passed）| PASS（artifact generated）|
| latest.json created | True（via ingestor）| PASS |
| test pass/fail counts | 56 passed / 17 failed | PASS |

### 5b. 失敗原因分析

| 失敗分類 | 件數 | 原因 |
|----------|------|------|
| test_book（title/price 驗證）| 4 | 程式碼 validation logic regression |
| test_excel_writer | 3 | header / price / column 欄位 bug |
| test_json_writer | 8 | FileNotFoundError / 欄位驗證失敗 |
| test_scraper_regressions | 1 | Excel control character stripping |
| test_http_client / test_windmill | 0 | PASS（網路 mock 類型）|

**結論：** 情境 A — 17 failures 為程式碼 regression，非網路外部依賴導致 pytest 無法執行。
不適用 `skip_test_result_check: true`。Artifact 正常產出，記錄在案。

---

## T6：Gate Policy 配置（情境 A）

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

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | repo_local（fallback_used=False）| PASS |
| signals after gate_policy | test_result_artifact_absent 消失；剩 closeout_file_missing + taxonomy_expansion_signal（audit-only）| PASS |
| gate.blocked | False（fail_mode=audit）| PASS |
| 選擇情境 | A（未使用 skip_test_result_check）| PASS |

---

## T7：Hook Coverage Tier 宣告

| Check | Actual |
|-------|--------|
| 日常使用 agent | GitHub Copilot（VS Code）|
| hook_coverage_tier declared | B（Copilot VS Code task，手動觸發）|

```yaml
# ── hook coverage tier ─────────────────────────────────────────────────────
# hook_coverage_tier: B   # Daily agent: GitHub Copilot (VS Code task triggering)
```

---

## T8：第二次 Session End Hook（有 gate_policy，有 test artifact）

```powershell
python .ai-governance-framework\governance_tools\session_end_hook.py `
  --project-root .
```

**實際輸出：**

```
ok=False  closeout_status=closeout_missing
policy_source=repo_local  fallback_used=False  repo_policy_present=True
fail_mode=audit  artifact_state=ok  blocked=False
failure_disposition: verdict_blocked=True  unknown=17  total=17
[SIGNAL] taxonomy_expansion_signal: unknown_count=17
canonical_audit_trend: entries_read=2/20  signal_ratio=50%  adoption_risk=True
[ADVISORY] adoption_risk: top_signals=[test_result_artifact_absent=1]
```

| Check | Actual | PASS/WARN/FAIL |
|-------|--------|----------------|
| policy_source | repo_local | PASS |
| signals | closeout_file_missing（structural）, taxonomy_expansion_signal（17 unknowns）, adoption_risk（advisory）| PASS |
| gate.blocked | False | PASS |
| signal_ratio (E8b) | 50%（2 entries，1 帶 test_result_artifact_absent）| PASS |
| adoption_risk | True（歷史第 1 筆有積壓 signal，正在好轉）| PASS |
| canonical_audit_log entries | 2/20 | PASS |

---

## 觀察重點（與 hp-oci-avalonia 比較）

| 觀察點 | hp-oci-avalonia（Tier B, C#）| Bookstore-Scraper（Tier B, Python）|
|--------|----------------------------|------------------------------------|
| test_result_artifact | structural absence → skip=true | real tests → 情境 A，已生成 artifact |
| hook coverage tier | B（Copilot VS Code task）| B（Copilot VS Code task）|
| 首次 signal_ratio | 50%（window dilution）| 100%（第 1 筆帶 signal）|
| 第二次 signal_ratio | —（未知）| 50%（第 2 筆 signal 減少）|
| gate_policy fallback | strict → blocked | strict → blocked（T4）|
| pre_task_check domain | 無 rules（fallback）| 有 rules → loaded bookstore-scraper pack |
| E8b trend | variable | 好轉中（signal_ratio 100%→50%）|

---

## API Bug 記錄（文件修正）

| Tool | 錯誤參數（舊文件）| 正確參數 | 修正狀態 |
|------|-----------------|---------|---------|
| `session_end_hook.py` | `--repo . --framework-root <path>` | `--project-root .` | ✅ 已修正（adoption-test-*.md, adoption-checklist.md）|
| `pre_task_check.py` | `--task-level L1` | `--risk L1` | ✅ 已修正（同上）|

---

## 整體通過門檻

| 項目 | 結果 |
|------|------|
| gate.blocked = False（T8）| ✅ |
| policy_source: repo_local（T6/T8）| ✅ |
| hook_coverage_tier 已宣告（T7）| ✅ B |
| test artifact 策略已釐清（T5/T6）| ✅ 情境 A |

**整體評分：8 / 8 tests PASS**

---

## 後續行動項目（Next Steps）

| 優先 | 項目 | 說明 |
|------|------|------|
| P1 | 修復 17 個 failing tests | test_book（validation）、test_json_writer（FileNotFoundError）等 regression |
| P1 | 建立 session-closeout.txt 工作流程 | 每次 session 結束前寫入 artifacts/session-closeout.txt（目前為 structural advisory）|
| P2 | commit submodule 更新 | `git add .ai-governance-framework && git commit` 釘住新版 `3120855` |
| P2 | 設定 VS Code Task 觸發 session_end_hook | Tier B 標準流程建立 |
| P3 | 修正 pytest pipeline | 考慮加入 conftest.py fixture 確保 artifact 路徑預先存在 |

---

## Agent 執行備註

- 測試 agent 名稱：GitHub Copilot（Claude Sonnet 4.6 backend）
- 測試日期：2026-04-13
- 測試環境：Windows PowerShell + Python 3.13.5（system）
- 本次測試的 hook coverage tier：B（手動執行）
- 備注：
  - `session_end_hook.py` 的 `--repo` / `--framework-root` 已被移除，正確參數為 `--project-root`
  - `pre_task_check.py` 的 `--task-level` 已改為 `--risk`，測試文件已更新
  - `UnicodeDecodeError`：Tee-Object 預設輸出 UTF-16 BOM，ingestor 需用 `Out-File -Encoding utf8`
  - `taxonomy_expansion_signal`（17 unknown failures）屬 audit-only，不 block gate，符合 `fail_mode=audit` 預期行為
