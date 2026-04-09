# Onboarding Payload Baseline

> 更新日期：2026-03-23  
> 類型：onboarding / adoption shaped payload 基線  
> 工具：`governance_tools/payload_audit_logger.py`

---

## Step 7 Rebaseline：framework onboarding 基線（2026-03-23）

> 任務：`Adopt governance baseline for external repo`  
> Commit：`37b2331`

| 欄位 | 值 |
|---|---|
| session_type | `onboarding` |
| ok | `true` |
| combined_estimate | `21088` |
| result_dict_total | `9208` |
| rendered_output | `11880` |
| warning_count | `4` |
| top fields | `pre_task_check`, `domain_contract`, `state`, `change_proposal`, `rule_pack_suggestions` |

### 與原始 onboarding baseline 的差異

| 項目 | 舊值 | Step 7 | 差異 |
|---|---:|---:|---:|
| combined_estimate | `60623` | `21088` | `-39535` |
| reduction | - | - | `-65.2%` |

說明：
- 這份 baseline 反映的是 framework onboarding path 的後期收斂，而不是早期 `Kernel-Driver-Contract` onboarding baseline
- 核心變化來自 `summary-first` 與 framework-self contract shape 的收斂
- runtime 不再把 onboarding task 視為一般 `L1` schema run

---

## Step 1：KDC Onboarding Baseline（2026-03-23）

### Session A：onboarding `ok=True`

| 類別 | Tokens | 佔比 |
|---|---:|---:|
| Governance + Domain Contract | `27640` | `45.6%` |
| Rendered output overhead | `32983` | `54.4%` |
| **Session total** | **`60623`** | `100%` |

### Session B：onboarding `ok=False`

> 錯誤：`Unknown rule packs: ['onboarding']`

| 類別 | Tokens | 佔比 |
|---|---:|---:|
| Governance + Domain Contract | `27215` | `45.2%` |
| Rendered output overhead | `32983` | `54.8%` |
| **Session total** | **`60198`** | `100%` |

說明：
- 早期 KDC onboarding 顯示，adoption logic 與 inline domain contract 會帶來很重的 rendered output
- failure case 也證明錯誤 scenario 仍可能產生高 payload 噪音

---

## KDC Summary-First Recheck（2026-03-23）

> 來源：`Kernel-Driver-Contract`  
> 路徑：`build_session_start_context()` + `summary_first`

| 欄位 | 值 |
|---|---|
| combined_estimate | `37142` |
| result_dict_total | `17170` |
| rendered_output | `19972` |
| domain_contract_tokens | `1840` |
| domain_contract_slim | `true` |
| summary_source | `kernel-driver-adapter-summary.md` |

### 與 KDC onboarding baseline 的差異

| 項目 | 舊值 | Summary-first | 差異 |
|---|---:|---:|---:|
| combined_estimate | `60623` | `37142` | `-23481` |
| domain_contract field | `13605` | `1840` | `-11765` |
| reduction | - | - | `-38.7%` |

說明：
- `kernel-driver-adapter-summary.md` 顯著降低了 domain contract 的直接輸入量
- onboarding payload 仍有相當比例留在 `pre_task_check` 與 rendered output
- 這說明 `summary-first` 有效，但 onboarding path 仍有後續優化空間

---

## 觀察重點

1. KDC onboarding path 的高 token 區主要來自 adoption logic 與 output shape
2. `kernel-driver-adapter-summary.md` 有效降低 domain contract payload
3. `summary-first` 能改善 onboarding path，但未完全消除 rendered output 開銷
4. 專用 onboarding short-circuit 仍屬 deferred optimization

## 一句總結

這份 baseline 顯示：onboarding path 的主要成本不只來自 domain contract，也來自 rendered output 與 adoption-specific flow；`summary-first` 已有幫助，但並非最終解。
