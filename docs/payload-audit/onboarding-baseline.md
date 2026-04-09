# Onboarding Payload Baseline

> 日期：2026-03-23  
> 範圍：onboarding / adoption shaped payload 量測  
> 工具：`governance_tools/payload_audit_logger.py`

---

## Step 7 Rebaseline：framework 自我 onboarding 形狀（2026-03-23）

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

### 與前一版 onboarding baseline 的差異

| 指標 | 舊值 | Step 7 | 差值 |
|---|---:|---:|---:|
| combined_estimate | `60623` | `21088` | `-39535` |
| reduction | - | - | `-65.2%` |

解讀：
- 這條路徑現在已明顯低於舊的 `Kernel-Driver-Contract` onboarding baseline。
- 主要收益來自 `summary-first` 與 framework-self contract shape，不只是一般 `L1` 壓縮。
- runtime 現在會為 onboarding task 另外產出 `onboarding-*.jsonl` lane。
- Windows 終端在 code page 無法編碼某些 Unicode 時，現在也能安全 fallback。

---

## Step 1：初始 KDC Onboarding Baseline（2026-03-23）

### Session A：onboarding `ok=True`

| 組件 | Tokens | 佔比 |
|---|---:|---:|
| Governance + Domain Contract | `27640` | `45.6%` |
| Rendered output overhead | `32983` | `54.4%` |
| **Session total** | **`60623`** | `100%` |

### Session B：onboarding `ok=False`

> 失敗原因：`Unknown rule packs: ['onboarding']`

| 組件 | Tokens | 佔比 |
|---|---:|---:|
| Governance + Domain Contract | `27215` | `45.2%` |
| Rendered output overhead | `32983` | `54.8%` |
| **Session total** | **`60198`** | `100%` |

解讀：
- 舊的 KDC onboarding 路徑主要成本不是 adoption logic 本身，而是厚重的 inline domain contract 加上大型 rendered output。
- 即使是 failure case，成本仍高，因為回傳 surface 仍然很大。

---

## KDC Summary-First Recheck（2026-03-23）

> 目標：`Kernel-Driver-Contract`  
> 模式：以 `build_session_start_context()` + `summary_first` 在 process 內量測

| 欄位 | 值 |
|---|---|
| combined_estimate | `37142` |
| result_dict_total | `17170` |
| rendered_output | `19972` |
| domain_contract_tokens | `1840` |
| domain_contract_slim | `true` |
| summary_source | `kernel-driver-adapter-summary.md` |

### 與舊 KDC onboarding baseline 的差異

| 指標 | 舊值 | Summary-first | 差值 |
|---|---:|---:|---:|
| combined_estimate | `60623` | `37142` | `-23481` |
| domain_contract field | `13605` | `1840` | `-11765` |
| reduction | - | - | `-38.7%` |

解讀：
- `kernel-driver-adapter-summary.md` 的填充帶來了真實下降，不只是預測值。
- 直接收益最大的仍是 `domain_contract` 這個 slice。
- onboarding 總成本仍然不低，因為 `pre_task_check` 與 rendered output 還是主要瓶頸。
- 這次重跑原本想產生新的 external JSONL audit，但被 sandbox 寫入限制擋住，所以改成 in-process 量測。

---

## 關鍵結論

1. 舊的 KDC onboarding path 成本高，主因不是 adoption logic，而是 contract 與 output shape。
2. `kernel-driver-adapter-summary.md` 已經上線，並且確實降低了 KDC onboarding 成本。
3. 下一個優化目標不再是「先把 KDC summary 填出來」，而是 onboarding path 的 `pre_task_check` 與 rendered output。
4. dedicated onboarding short-circuit 仍可測，但應先確認它是否真的能壓到這兩個剩餘主成本來源。

## 下一步

1. 降低 KDC onboarding path 的 `pre_task_check` 成本。
2. 降低同一路徑的 rendered output 大小。
3. 在 `summary-first` 已就位後，重新判斷 onboarding 是否仍值得獨立 short-circuit。
4. 當外部 repo 的 `docs/payload-audit/` 可寫之後，重新跑一次真正的 external-repo onboarding audit。
