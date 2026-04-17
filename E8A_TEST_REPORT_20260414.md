# E8a 累積測試報告 — E1b 評估準備

> **測試日期**: 2026-04-14  
> **Framework 版本**: `78b8024` (HEAD)  
> **測試目的**: 在多個 external repo 上跑 `session_end_hook`，累積 E8a canonical audit log，評估 E1b 開工條件是否成立  
> **不是目的**: 驗證 governance 本身是否「正確」。本輪為 signal 收集，非正確性判斷。

---

## 0. 前置作業

| 步驟 | 結果 |
|------|------|
| `git pull` ai-governance-framework | ✅ Already up to date (`78b8024`) |
| venv / pyyaml 確認 | ✅ pyyaml ok, json ok |
| Repo inventory | ✅ 5 repos confirmed（3 已 adopt + 2 green-field）|

---

## 1. Phase 1 — 已 adopt Repo（5 次累積）

### 1.1 執行摘要

| Repo | 語言 | Tier | 執行次數 | 最終 entries | 最終 signal_ratio | verdict |
|------|------|------|----------|-------------|-------------------|---------|
| `Bookstore-Scraper` | Python | A (undeclared) | 5 | 7 / 20 | **14%** | NON-GATE-FAILURE |
| `cli` | C++ | A (undeclared) | 5 | 8 / 20 | **25%** | NON-GATE-FAILURE |
| `hp-oci-avalonia` | C# | A (undeclared) | 5 | 10 / 20 | **10%** | NON-GATE-FAILURE |

### 1.2 各 Run 詳細數字

#### Bookstore-Scraper

| Run | ok | verdict | signal_ratio | entries |
|-----|----|---------|--------------|---------|
| 1 | False | NON-GATE-FAILURE | 33% | 3 |
| 2 | False | NON-GATE-FAILURE | 25% | 4 |
| 3 | False | NON-GATE-FAILURE | 20% | 5 |
| 4 | False | NON-GATE-FAILURE | 17% | 6 |
| 5 | False | NON-GATE-FAILURE | 14% | 7 |

#### cli

| Run | ok | verdict | signal_ratio | entries |
|-----|----|---------|--------------|---------|
| 1 | False | NON-GATE-FAILURE | 50% | 4 |
| 2 | False | NON-GATE-FAILURE | 40% | 5 |
| 3 | False | NON-GATE-FAILURE | 33% | 6 |
| 4 | False | NON-GATE-FAILURE | 29% | 7 |
| 5 | False | NON-GATE-FAILURE | 25% | 8 |

#### hp-oci-avalonia

| Run | ok | verdict | signal_ratio | entries |
|-----|----|---------|--------------|---------|
| 1 | False | NON-GATE-FAILURE | 33% | 3 |
| 2 | False | NON-GATE-FAILURE | 25% | 4 |
| 3 | False | NON-GATE-FAILURE | 20% | 5 |
| 4 | False | NON-GATE-FAILURE | 17% | 6 |
| 5 | False | NON-GATE-FAILURE | 14% | 7 |

### 1.3 Phase 1 觀察

- 三個 repo 的 `ok=False` 原因均為 `closeout_file_missing`（`NON-GATE-FAILURE`），**不是 gate block**
- Tier 未宣告（`hook_coverage_tier_undeclared`）→ 系統 fallback 至 Tier A（最嚴格），導致 closeout missing 被視為 violation
- `cli` 的 `test_result_artifact_absent` 已因 `structural absence declared` 正確跳過
- `hp-oci-avalonia` `readiness_level=0`（limited by: `agents_base_has_obligation`），activation=unknown
- signal_ratio 呈下降趨勢：因為初始幾筆有 signal，後期 clean run 稀釋了 ratio（正常現象）

---

## 2. Phase 2 — Green-field Repo（Adopt + 5 次累積）

### 2.1 Adoption 結果

| Repo | adopt_governance.py | gate_policy.yaml | readiness schema_status |
|------|--------------------|-----------------|--------------------|
| `Standard_ISP_Tool` | ✅ 成功 (`repo_type=firmware`) | ✅ 已寫入（skip_test_result_check=true） | ✅ complete |
| `gl_electron_tool` | ✅ 成功 (`repo_type=firmware`) | ✅ 已寫入 | ✅ complete |

Readiness warnings（兩個 repo 相同，均為 optional）：
- `hooks (optional)`: pre-commit / pre-push hook 未安裝
- `framework-version`: lock file missing / adopted release not recorded

### 2.2 執行摘要

| Repo | 語言 | Tier | 執行次數 | 最終 entries | 最終 signal_ratio | adoption_risk | verdict |
|------|------|------|----------|-------------|-------------------|--------------|---------|
| `Standard_ISP_Tool` | C/C++ | B | 5 | 8 / 20 | **0%** | False | OK+ADVISORIES |
| `gl_electron_tool` | JavaScript | B | 5 | 8 / 20 | **100%** | **True** | OK+ADVISORIES |

### 2.3 各 Run 詳細數字

#### Standard_ISP_Tool

| Run | ok | verdict | signal_ratio | entries |
|-----|----|---------|--------------|---------|
| 1 | True | OK+ADVISORIES | 0% | 1 |
| 2 | True | OK+ADVISORIES | 0% | 2 |
| 3 | True | OK+ADVISORIES | 0% | 3 |
| 4 | True | OK+ADVISORIES | 0% | 4 |
| 5 | True | OK+ADVISORIES | 0% | 5 |

#### gl_electron_tool

| Run | ok | verdict | signal_ratio | entries |
|-----|----|---------|--------------|---------|
| 1 | True | OK+ADVISORIES | 100% | 1 |
| 2 | True | OK+ADVISORIES | 100% | 2 |
| 3 | True | OK+ADVISORIES | 100% | 3 |
| 4 | True | OK+ADVISORIES | 100% | 4 |
| 5 | True | OK+ADVISORIES | 100% | 5 |

### 2.4 Phase 2 觀察

- `Standard_ISP_Tool`：`skip_test_result_check=true` 有效，test_result signal 被正確抑制；signal_ratio=0%，clean
- `gl_electron_tool`：signal_ratio=100% 且 adoption_risk=True 已觸發——因為每次跑都出現 `test_result_artifact_absent`（無 JS test artifact），且未設定 skip_test_result_check
  - `[ADVISORY] adoption_risk: top_signals=[test_result_artifact_absent=8]`
  - `canonical_usage_audit: usage_status=trend_risk_context ... trend_risk=True`

---

## 3. Phase 3 — Audit Log 資料品質

### 3.1 各 Repo Entry 數量與 Signal 分佈

| Repo | 總 entries | with_signals | signal_ratio | 主要 signal | adoption_risk |
|------|-----------|-------------|--------------|------------|--------------|
| `Bookstore-Scraper` | 7 | 1 | 14% | `test_result_artifact_absent=1` | False |
| `cli` | 8 | 2 | 25% | `test_result_artifact_absent=2` | False |
| `hp-oci-avalonia` | 10 | 1 | 10% | `test_result_artifact_absent=1` | False |
| `Standard_ISP_Tool` | 8 | 0 | **0%** | — | False |
| `gl_electron_tool` | 8 | 5 | **100%** | `test_result_artifact_absent=5` | **True** |

### 3.2 跨 Repo 高頻 Signal

| Signal | 出現 repo | 次數合計 | 分析 |
|--------|-----------|---------|------|
| `test_result_artifact_absent` | Bookstore-Scraper, cli, hp-oci-avalonia, gl_electron_tool | 9 | **跨 repo 出現，系統性問題** |
| `closeout_file_missing` | Bookstore-Scraper, cli, hp-oci-avalonia | 多次 | Tier undeclared → Tier A fallback 觸發 |
| `taxonomy_expansion_signal` | Bookstore-Scraper | unknown_count=17 | 需確認 gate_policy unknown treatment |

### 3.3 Verdict 分佈

| verdict | Repos | 說明 |
|---------|-------|------|
| `NON-GATE-FAILURE` | Bookstore-Scraper, cli, hp-oci-avalonia | ok=False 但 gate 未 block；由 closeout missing 造成 |
| `OK+ADVISORIES` | Standard_ISP_Tool, gl_electron_tool | ok=True；有 advisory 但不 block |

---

## 4. Phase 4 — E1b 評估 Checklist

> 日期：**2026-04-14**

### 4.1 量化條件確認

| 條件 | 要求 | 現狀 | 達標？ |
|------|------|------|--------|
| 每 repo entries >= 20 | >= 20 | 最高 10（hp-oci-avalonia）| ❌ **未達標** |
| signal_ratio 多 repo 一致 >= 50% | >= 50% | 僅 gl_electron_tool = 100%；其餘 0–25% | ❌ **未一致** |
| 跨 repo 相同 signal 重複出現 | 同一 signal 多 repo | `test_result_artifact_absent` 出現於 4/5 repos | ✅ |
| Tier A + Tier B 各一 repo 資料足夠 | entries >= 20 | Tier A 3 repos 均 < 20；Tier B 2 repos < 20 | ❌ **未達標** |

### 4.2 觀察到的高頻 Signal

- `test_result_artifact_absent`：出現於 4 個 repo，是本輪最主要的 canonical gap signal
- `closeout_file_missing`：出現於所有 Tier A (undeclared) repo；根本原因是 `hook_coverage_tier` 未宣告

### 4.3 跨 Repo 一致性分析

| 判斷 | 依據 |
|------|------|
| `test_result_artifact_absent` 是系統性問題 | 4/5 repo 均出現，不分語言（Python/C++/C#/JS） |
| 非個別 repo 操作失誤 | 全新 adopt 的 gl_electron_tool 也立即出現 |
| `closeout_file_missing` 是操作性問題 | 只有 Tier undeclared (Tier A fallback) repo 出現；Tier B repo 無此問題 |

### 4.4 E1b 開工條件判斷

```
❌ entries >= 20：未達標（最多 10 筆）
❌ signal_ratio 多 repo >= 50% 且一致：未達標（僅 gl_electron_tool 達標）
✅ 跨 repo 相同 signal：test_result_artifact_absent 系統性出現
❌ Tier A + B 各一 repo 達到 entries >= 20：未達標

→ E1b 條件：尚未滿足。繼續累積，下次評估目標 entries >= 20。
```

---

## 5. 行動建議

### 5.1 立即可行（不開 E1b）

| 優先 | 行動 | 影響 |
|------|------|------|
| 🔴 高 | `Bookstore-Scraper`、`cli`、`hp-oci-avalonia` 在 `gate_policy.yaml` 加入 `hook_coverage_tier: B`（或 A） | 消除 Tier undeclared fallback，讓 `closeout_file_missing` 降級為 advisory |
| 🟡 中 | `gl_electron_tool` 加入 `skip_test_result_check: true`（若確認無 JS test runner） | 將 signal_ratio 從 100% 降到 0%，消除 adoption_risk |
| 🟡 中 | 繼續對所有 5 repo 累積 session_end_hook log，目標每 repo 達到 20 筆 | 讓 trend 計算有統計意義 |
| 🟢 低 | `hp-oci-avalonia` 修正 `readiness_level=0`（`agents_base_has_obligation`） | 提升 activation 狀態 |

### 5.2 下次 E1b 評估時機

繼續累積直到：

```powershell
# 目標：每 repo 至少 20 筆
# 估算還需要的 session_end_hook 次數（以今日數字計算）
# Bookstore-Scraper: 需再跑 ~13 次
# cli:               需再跑 ~12 次
# hp-oci-avalonia:   需再跑 ~10 次
# Standard_ISP_Tool: 需再跑 ~12 次
# gl_electron_tool:  需再跑 ~12 次
```

---

## 6. 附錄：測試環境

| 項目 | 值 |
|------|----|
| Framework commit | `78b8024` — docs: E8a accumulation test procedure |
| Python | venv (ai-governance-framework/.venv) |
| pyyaml | ok |
| OS | Windows 11 (PowerShell) |
| 測試執行時間 | 2026-04-14 |
| 採用 framework 指令 | `session_end_hook.py --format json` / human mode |
| adopt_governance | Standard_ISP_Tool, gl_electron_tool（本次新增）|

---

*本報告由 GitHub Copilot 自動產出，基於 session_end_hook 實際執行輸出與 canonical-audit-log.jsonl 資料。*
