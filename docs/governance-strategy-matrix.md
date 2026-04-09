# Governance Strategy Matrix：依 agent class 對應治理策略

## 目的

這份文件定義不同 agent class 應採用的 governance strategy。
核心原則是：

> 不應因為 agent capability 看起來可以接受 injection，就把 injection 誤當成可替代 enforcement 的 authority。

這份 matrix 用來回答：
- 不同 agent class 應採用哪種 injection posture
- enforcement 應維持到什麼程度
- observation 應如何配合

## 核心原則

> Injection is advisory. Enforcement is authoritative.

這句話代表：
- 即使 injection 很完整，也不能把 agent 的 policy consumption 視為裁決依據
- 真正的 enforcement 必須來自 hooks、runtime boundary、artifact review 或其他外部機制

## Agent Class 對應策略

### `instruction_capable`

特徵：
- 可讀 repo context
- 可持續承載 instruction
- hooks / tool gate 可接入
- context window 與 trust posture 相對穩定

對應策略：

| 面向 | 策略 | 說明 |
|---|---|---|
| Injection | full advisory payload | 可載入 selected rules、escalation triggers、hard prohibitions |
| Enforcement | pre_task + post_task + session_end | hook 不能因 injection 存在而弱化 |
| Observation | consumption + execution signals | 同時觀測 payload 是否被看見，以及 runtime evidence / coverage |

`governance_strategy`: `injection+enforcement`  
`injection_reliance`: `none`

### `instruction_limited`

特徵：
- context window 較短，persistent instruction 較弱
- hook / tool gate 可能存在，但穩定度不足
- trust posture 不應假設與 instruction-capable 相同

對應策略：

| 面向 | 策略 | 說明 |
|---|---|---|
| Injection | minimal payload only | 只放 hard prohibitions、escalation triggers、reviewer hints |
| Enforcement | pre_task + post_task 為主 | 仍依賴 task level、validator、warning 與外部 enforcement |
| Observation | execution 為主 | consumption observation 較弱，不把 injection 視為可驗證前提 |

`governance_strategy`: `minimal_injection+enforcement`  
`injection_reliance`: `none`

### `wrapper_only`

特徵：
- 不被視為可靠的 policy consumption surface
- 主要依賴外部 wrapper 或 hooks
- file access / instruction persistence 不足以支撐 injection 信任

對應策略：

| 面向 | 策略 | 說明 |
|---|---|---|
| Injection | none | 不把 policy payload 當成主要控制面 |
| Enforcement | external wrapper + session boundary | 依賴 wrapper、artifact review、session closeout |
| Observation | artifact review + post-execution only | 不主張 consumption observation |

`governance_strategy`: `no_injection+strict_enforcement`  
`injection_reliance`: `none`

## 常見風險

| 風險類型 | 失真形式 | 說明 |
|---|---|---|
| 把 injection 當成 policy 已被遵守 | `false_allow` | 應由 enforcement 補上，而不是信任 payload |
| 有 observation 就高估 enforcement 完整度 | `false_confidence` | artifact 很完整，不代表 runtime 已被真正治理 |
| capability 分類錯誤 | `governance_bypass` | 用錯 agent class 會讓策略整體失真 |

## `governance_strategy` 欄位

目前允許值：

```text
injection+enforcement
minimal_injection+enforcement
no_injection+strict_enforcement
```

這些值描述的是 session 的治理姿態，不是 agent 的產品定位或品牌名稱。

## `injection_reliance` 欄位

目前允許值：

```text
none
partial
high
```

目前預設應維持 `none`，表示 enforcement 不依賴 advisory injection 的成功與否。

## 例子 mapping

| Surface | 推定治理策略 | 對應 class |
|---|---|---|
| `claude_code` + repo-local instruction + hooks | `injection+enforcement` | `instruction_capable` |
| `codex` 經 adapter 使用 | `minimal_injection+enforcement` | `instruction_limited` |
| 只有 API、沒有 hooks | `no_injection+strict_enforcement` | `wrapper_only` |

## 一句總結

這份 matrix 不在宣稱每種 agent 都能被完整治理；它只在說明：不同 capability profile 應採用不同的治理策略，而且 injection 與 enforcement 不能混成同一件事。
