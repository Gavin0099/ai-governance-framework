# L1 Payload Baseline

> 最後更新：2026-03-23（Step 5b+6 完成）
> 樣本數：3 批次（Step 1–3 × Hearth+KDC；Step 4–5 × ai-governance-framework；Step 5b+6 × ai-governance-framework）
> Token 計算方式：estimate（JSON 字元數 ÷ 4）
> Tool：`governance_tools/payload_audit_logger.py`

---

## 說明

這份文件保存 `L1` 路徑在 payload audit 中的基準值與 rebaseline 結果。  
它主要用途是：

- 追蹤 L1 engineering path 的 payload 變化
- 觀察 rule pack、state、proposal 等欄位在 runtime 中的重量
- 提供後續優化與 adoption 對照基準

## Step 7 Rebaseline -- ai-governance-framework (2026-03-23)

> Task: `Refactor state generator module`
> Commit: `37b2331`

| Field | Value |
|------|------|
| session_type | `L1` |
| ok | `true` |
| combined_estimate | `21564` |
| result_dict_total | `9345` |
| rendered_output | `12219` |
| warning_count | `5` |
| top fields | `pre_task_check`, `domain_contract`, `state`, `change_proposal`, `rule_pack_suggestions` |

### Delta vs prior L1 baseline

| Metric | Prior | Step 7 | Delta |
|------|------:|--------:|------:|
| combined_estimate | `20539` | `21564` | `+1025` |

Interpretation:
- Step 7 did not reduce the generic L1 path by itself.
- The dominant costs are still `pre_task_check` and `domain_contract`, not the old free-form output surface.
- The next meaningful optimization target remains domain-summary/onboarding shaping rather than more output-tier work alone.

---

## Step 5b+6 最終量測（ai-governance-framework，2026-03-23）

> L1 baseline（domain_contract auto-discovered，summary-first）

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always + on-demand × 7） | ~1,860 | 9% |
| pre_task_check | ~8,500 | 41% |
| state | ~865 | 4% |
| change_proposal | ~647 | 3% |
| domain_contract（summary-first） | ~8,500 | 41% |
| level_decision / repo_type 等新欄位 | ~127 | 1% |
| **Session 總計** | **~20,539** | 100% |

**對比 L0（6,451）：L1 多出 ~14,088 tokens（+218%）— 主要來自 domain_contract 載入。**

---

## Step 4+5 重測（ai-governance-framework，2026-03-23）

> Task: `"refactor state generator module"` → 明確指定 L1

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always + on-demand × 7） | ~1,860 | 18% |
| pre_task_check | ~4,549 | 43% |
| state | ~865 | 8% |
| change_proposal | ~647 | 6% |
| domain_contract（auto-discovered） | ~3,522 | 34% |
| level_decision / repo_type 等新欄位 | ~114 | 1% |
| **Session 總計** | **~10,457** | 100% |

### Step 4 新增的 context-aware rule 分類

| 欄位 | 值 |
|------|-----|
| `repo_type` | `"service"` |
| `context_aware_rules` | `["common", "python"]` |
| `authority_filter.allowed_count` | 7 |
| `authority_filter.include_on_demand` | `true` |

**repo_type 偵測說明：** ai-governance-framework 含有 `pyproject.toml` 和 `.py` 檔案，
偵測為 `service`。`_SCAN_EXCLUDED_DIRS` 確保 `examples/usb-hub-contract/fixtures/src/usb_hub.c`
不觸發 `firmware` 誤判（Step 4 bug fix）。

---

## Step 1–3 初始 baseline（Hearth repo，2026-03-23）

### Session A — L1，無 domain contract（Hearth repo）

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always + on-demand） | ~5,166 | 21% |
| Domain Contracts | ~3,360 | 14% |
| State（含 refactor rules proposal） | ~1,712 | 7% |
| Change Proposal | ~362 | 1% |
| Rendered output overhead | ~14,143 | 57% |
| **Session 總計** | **~24,743** | 100% |

### Session B — L1，含 domain contract（Kernel-Driver-Contract）

| 類別 | Token 數 | 占比 |
|------|---------|------|
| Governance 文件（always + on-demand） | ~14,035 | 23% |
| Domain Contracts（KDC，rich contract） | ~13,605 | 22% |
| State | ~393 | 1% |
| Validator preflight | ~252 | 0% |
| Rendered output overhead | ~32,338 | 53% |
| **Session 總計** | **~60,623** | 100% |

**關鍵發現：有 rich domain contract（KDC）的 L1 session 比無 contract 多 ~2.45×**

---

## Top 3 Token 黑洞（Step 4+5 重測 — ai-governance-framework）

| 排名 | 欄位 | Token | 占比 |
|------|------|-------|------|
| 🥇 1 | `pre_task_check` | ~4,549 | ~43% |
| 🥈 2 | `domain_contract` | ~3,522 | ~34% |
| 🥉 3 | `state` | ~865 | ~8% |

**Runner-up：** `change_proposal` (~647) · `level_decision` (~60) · `authority_filter` (~54)

---

## Step 4 Domain Adapter Summary 現況

| 狀態 | 詳情 |
|------|------|
| kernel-driver-adapter-summary.md | ✅ 已建立，且 `kernel-driver` summary loader 會實際解析這份 live adapter |
| inject_domain_summary | ✅ 已實作，session_start 注入點已接入 |
| KDC 實際啟用 | ✅ summary-first 已在 `Kernel-Driver-Contract` 上量到實際效果 |
| 已量測效益（KDC） | `13605` → `1840` tok（`-86.5%`） |

---

## Authority Filter 確認（L1 — Step 5 後）

| 文件 | L1 載入 | 符合預期 |
|------|--------|---------|
| SYSTEM_PROMPT.md | ✅ | ✅ |
| AGENT.md | ✅ | ✅ |
| PLAN.md | ✅ | ✅ |
| ARCHITECTURE.md | ✅ | ✅（on-demand，L1 載）|
| TESTING.md | ✅ | ✅（on-demand，L1 載）|
| REVIEW_CRITERIA.md | ❌ | ✅（human-only，永不）|
| HUMAN-OVERSIGHT.md | ❌ | ✅（human-only，永不）|

## Step 4+5 新增欄位確認

| 欄位 | 出現在 L1 payload | 值 |
|------|------------------|-----|
| `task_level` | ✅ | `"L1"` |
| `level_decision.requested` | ✅ | `"L1"` |
| `level_decision.upgraded` | ✅ | `false` |
| `repo_type` | ✅ | `"service"` |
| `context_aware_rules` | ✅ | `["common","python"]` |
| `authority_filter.include_on_demand` | ✅ | `true` |
