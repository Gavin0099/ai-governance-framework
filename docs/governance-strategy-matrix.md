# Governance Strategy Matrix：依 agent class 對應治理策略

## 目的

這份文件定義：不同 agent class 應對應哪一種 governance strategy。

核心原則是：

> 不要把 agent capability 當成 injection 成功與否的保證。  
> injection 是 advisory，enforcement 才是 authoritative。

因此，這份 matrix 要回答的是：

- 不同 agent class 應承擔多少 injection
- enforcement 應補到什麼程度
- observation 要看哪些面向

## 核心原則

> Injection is advisory. Enforcement is authoritative.

換句話說：

- 即使 injection 存在，也不能假定 agent 已消化規則
- 若 enforcement 不足，不能靠多塞 payload 補救

## 三種策略類型

### `instruction_capable`

特徵：

- 具穩定 repo context
- 可承載 persistent instruction
- hooks / tool gate 可用
- context window 與 trust posture 較完整

對應策略：

| 面向 | 策略 | 說明 |
|---|---|---|
| Injection | full advisory payload | 可承載較完整 selected rules、escalation triggers、hard prohibitions |
| Enforcement | pre_task + post_task + session_end | hook 足以補足 injection 不可靠之處 |
| Observation | consumption + execution signals | 可同時觀察 payload 是否進入 surface，以及 runtime 是否有 evidence / coverage |

`governance_strategy`: `injection+enforcement`  
`injection_reliance`: `none`

### `instruction_limited`

特徵：

- context window 較弱或 persistent instruction 不穩
- hook / tool gate 仍可用
- trust posture 中等或偏低

對應策略：

| 面向 | 策略 | 說明 |
|---|---|---|
| Injection | minimal payload only | 只保留 hard prohibitions、關鍵 escalation triggers、最小 reviewer hints |
| Enforcement | pre_task + post_task（較保守） | task level、validator、warning 面向更依賴 enforcement |
| Observation | execution 為主 | consumption observation 較弱，不能高估 injection 成效 |

`governance_strategy`: `minimal_injection+enforcement`  
`injection_reliance`: `none`

### `wrapper_only`

特徵：

- 幾乎沒有可信的 policy consumption surface
- 可能沒有 hooks
- file access / instruction persistence 不穩或不可驗

對應策略：

| 面向 | 策略 | 說明 |
|---|---|---|
| Injection | none | 不再假裝 policy payload 有穩定落點 |
| Enforcement | external wrapper + session boundary | 主要靠外層 wrapper、artifact review、session closeout |
| Observation | artifact review + post-execution only | 不主張 consumption observation |

`governance_strategy`: `no_injection+strict_enforcement`  
`injection_reliance`: `none`

## 失敗模式

| 失敗模式 | 風險 | 說明 |
|---|---|---|
| 把 injection 當成 policy 已被吸收 | `false_allow` | 會讓 enforcement 缺口被掩蓋 |
| observation 太弱卻假裝 enforcement 完整 | `false_confidence` | artifact 看似齊全，實際 runtime 不可見 |
| capability 被高估 | `governance bypass` | 會把本應保守的 class 錯當成高能力 class |

## `governance_strategy` 欄位

允許值：

```text
injection+enforcement
minimal_injection+enforcement
no_injection+strict_enforcement
```

它描述的是這個 session 目前採用的治理姿態，不是 agent 的本體能力。

## `injection_reliance` 欄位

允許值：

```text
none
partial
high
```

目前預設應保守使用 `none`，避免把 advisory injection 誤讀成 runtime authority。

## 目前 mapping 範例

| Surface | 建議策略 | 預設 class |
|---|---|---|
| `claude_code` + repo-local instruction + hooks | `injection+enforcement` | `instruction_capable` |
| `codex` 類 adapter | `minimal_injection+enforcement` | `instruction_limited` |
| 外部 API / 無 hooks | `no_injection+strict_enforcement` | `wrapper_only` |

## 一句話結論

這份 matrix 的目的，不是證明哪個 agent 比較強，而是把不同 capability profile 應採用的治理姿態固定下來，避免 injection 與 enforcement 被混為一談。
