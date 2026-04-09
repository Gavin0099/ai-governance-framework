# L0 Payload Baseline

> 最後更新：2026-03-23（Step 5b+6 完成，L0 domain gate 生效）
> 量測批次：3 批次（Step 1–3 / Step 4–5 / Step 5b+6）
> Token 計算方式：estimate（JSON 字元數 ÷ 4）
> Tool：`governance_tools/payload_audit_logger.py`

---

## 說明

這份文件保存 `L0` 路徑在 payload audit 中的基準值與 rebaseline 結果。  
它主要用途是：

- 比較 Step 1 與 Step 7 的 token 變化
- 觀察 L0 path 是否因 domain gate 與裁剪邏輯而明顯收斂
- 提供後續 reviewer / adopter 一個可比對的 baseline

## Step 7 Rebaseline -- ai-governance-framework (2026-03-23)

> Task: `Update button label in UI`
> Commit: `37b2331`

| Field | Value |
|------|------|
| session_type | `L0` |
| ok | `true` |
| output_tier | `1` |
| combined_estimate | `6550` |
| result_dict_total | `2256` |
| rendered_output | `4294` |
| domain_contract_loaded | `false` |
| tier3_artifact_ref | none |

### Delta vs prior L0 baseline

| Metric | Prior | Step 7 | Delta |
|------|------:|--------:|------:|
| combined_estimate | `6451` | `6550` | `+99` |

Interpretation:
- Step 7 preserved the low L0 budget.
- Output-tier separation did not materially reduce this path further.
- The L0 fast path is still operating as intended: `output_tier=1`, no domain contract load.

---

## ✅ Step 5b+6 最終量測（L0 domain gate 生效後）

> Task: UI 純改動任務 → 自動偵測為 L0，domain_contract 跳過

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always-load × 4） | ~1,130 | 18% |
| pre_task_check（domain 已跳過） | ~3,200 | 50% |
| state | ~827 | 13% |
| change_proposal | ~603 | 9% |
| level_decision / repo_type 等新欄位 | ~97 | 2% |
| domain_contract | **0**（gate 跳過） | 0% |
| **Session 總計** | **~6,451** | 100% |

### Target 達成確認

| 目標 | 設定 | Step 4+5（未達標）| Step 5b+6（最終）| 狀態 |
|------|------|-----------------|-----------------|------|
| L0 < 9,665 tok | 目標 | 10,264 ❌ | **6,451** ✅ | **達標** |
| vs L1 delta | 顯著差距 | −193 tok（−1.9%） | **−14,088 tok（−68.6%）** | ✅ |
| domain_contract 跳過 | L0 = 0 | 3,522（未跳過） | **0** | ✅ |
| forbidden files 排除 | 4 項 | ✅ | ✅ | ✅ |

**68.6% token reduction（L0 vs L1）— 遠超原設定目標**

### Bug fix 說明（Step 5b）

`contract_file = None` 不足以阻止 domain contract 載入：
`resolve_contract()` 會從 `project_root` 自動 discover `contract.yaml`。

修正：在 `run_pre_task_check()` 加入 `skip_domain_contract: bool = False` 參數，
L0 gate 命中時直接 bypass discovery，不進入 resolve 流程。

同時修正 `payload_audit_logger.py`：改用 `result["task_level"]` 決定 session_type，
確保 L0 runs 寫到 `L0-*.jsonl`（原本寫到 `L1-*.jsonl`）。

---

## Step 4+5 重測（gate 前，2026-03-23）

> Task: `"update button label in UI"` → L0，domain_contract 仍載入

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always-load × 4） | ~1,130 | 11% |
| pre_task_check | ~4,485 | 44% |
| state | ~827 | 8% |
| change_proposal | ~603 | 6% |
| **domain_contract（仍載入）** | **~3,522** | **34%** |
| level_decision / repo_type 等新欄位 | ~97 | 1% |
| **Session 總計** | **~10,264** | 100% |

---

## Step 1–3 初始 baseline（Hearth repo，2026-03-23）

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always-load） | ~3,954 | 20% |
| Domain Contracts | ~3,360 | 17% |
| Rendered output overhead | ~11,106 | 57% |
| **Session 總計** | **~19,330** | 100% |

---

## L0 vs L1 比較（Step 5b+6 後）

| | L0（gate 後） | L1 baseline | L0 節省 |
|-|--------------|-------------|---------|
| domain_contract | **0** | ~12,000+ | ✅ |
| auth_files | 4 | 7 | ✅ |
| **總計** | **~6,451** | **~20,539** | **−14,088（−68.6%）** |

---

## Authority Filter 確認（L0 — Step 5b+6 後）

| 文件 | L0 載入 | 符合預期 |
|------|--------|---------|
| SYSTEM_PROMPT.md | ✅ | ✅ |
| AGENT.md | ✅ | ✅ |
| PLAN.md | ✅ | ✅ |
| ARCHITECTURE.md | ❌ | ✅（forbidden_load，L0 強制排除）|
| NATIVE-INTEROP.md | ❌ | ✅（forbidden_load，L0 強制排除）|
| REVIEW_CRITERIA.md | ❌ | ✅（human-only，永不）|
| HUMAN-OVERSIGHT.md | ❌ | ✅（human-only，永不）|
| domain_contract | ❌ | ✅（L0 domain gate，skip policy）|

## Payload 欄位確認（Step 5b+6 後）

| 欄位 | 值 |
|------|-----|
| `task_level` | `"L0"` |
| `level_decision.final` | `"L0"` |
| `level_decision.upgraded` | `false` |
| `repo_type` | `"service"` |
| `context_aware_rules` | `["common","python"]` |
| `authority_filter.include_on_demand` | `false` |
| `domain_contract` | `null`（gate 跳過）|
| audit `session_type` | `"L0"`（bug fix 後正確）|
