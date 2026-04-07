# Governance Strategy Matrix

## 目的

這份文件定義「對不同 agent class，治理策略應該發生在哪一層、用什麼方式執行」。

它回答的核心問題不是：

> 要注入什麼？

而是：

> 這個 agent 要用哪種治理策略？

這是 Runtime Injection Layer 的路由決策層。它依據 agent capability 決定策略，
injection 只是其中一條路，不是預設也不是終點。

---

## 核心原則

> **Injection is advisory. Enforcement is authoritative.**
>
> 治理策略的選擇必須以 enforcement 能獨立成立為前提。
> 沒有任何策略可以把 injection 的成功當成 enforcement 的依賴。

---

## 策略矩陣

### `instruction_capable`

**Capability profile**:
- `has_file_access: true`
- `supports_persistent_instruction: true`
- `supports_tool_gate: true`
- `context_window: full`
- `trust_level: high`

**治理策略**:

| 層 | 動作 | 說明 |
|----|------|------|
| Injection | full advisory payload | 注入 selected rules / escalation triggers / hard prohibitions |
| Enforcement | pre_task + post_task + session_end | 完整 hook 路徑，不依賴 injection 是否被理解 |
| Observation | consumption + execution signals | 記錄 context loaded、surface coverage、memory integrity |

**`governance_strategy`**: `injection+enforcement`

**`injection_reliance`**: `none`（enforcement 路徑完全獨立，injection 只是輔助）

**失敗模式**:
- injection payload 被壓縮 → enforcement 仍然成立（因為 hook 獨立）
- agent 誤解規則 → post_task 仍然攔截 policy violation

---

### `instruction_limited`

**Capability profile**:
- `supports_persistent_instruction: false` 或 `context_window: limited`
- `supports_tool_gate: true`（hook 仍然可用）
- `trust_level: medium` 或 `low`

**治理策略**:

| 層 | 動作 | 說明 |
|----|------|------|
| Injection | minimal payload only | 只注入 hard prohibitions；不注入完整 rule pack |
| Enforcement | pre_task + post_task（stricter threshold） | task_level 預設抬升；violation threshold 收緊 |
| Observation | execution signals only | 不要求 consumption evidence（因為 context 不穩定） |

**`governance_strategy`**: `minimal_injection+enforcement`

**`injection_reliance`**: `none`（injection 的存在不影響 enforcement 判斷）

**失敗模式**:
- injection 被 agent 忽略 → enforcement hook 仍然獨立觸發
- context 被裁切 → 記錄為 `context_degraded` signal，不 block，但抬升 task level

**注意**:
對 instruction_limited agent，injection 的目的是「提示」而非「規範」。
任何期待 instruction_limited agent 把 injection 當 contract 的設計都是錯誤假設。

---

### `wrapper_only`

**Capability profile**:
- `supports_tool_gate: false` 或 `trust_level: untrusted`
- 不可信任其 policy consumption
- 可能沒有 file access 或無法承載 session-level instruction

**治理策略**:

| 層 | 動作 | 說明 |
|----|------|------|
| Injection | **none** | 不注入任何 policy；浪費資源且製造虛假「已治理」感 |
| Enforcement | external wrapper + session boundary | 不依賴 agent 內部；只在 session 邊界攔截 |
| Observation | artifact review + post-execution only | 只做事後審查，不做 consumption observation |

**`governance_strategy`**: `no_injection+strict_enforcement`

**`injection_reliance`**: `none`（沒有 injection，enforcement 必須完全獨立）

**失敗模式**:
- 沒有 pre/post hook → 只能在 session 結束後審查 artifact
- capability 被高估（誤判為 instruction_capable） → `governance bypass` 風險

**警告**:
對 wrapper_only agent 設計 injection 路徑是架構錯誤，不是 degraded graceful fallback。
此 class agent 的唯一可信 governance 路徑是外部邊界。

---

## 失敗模型

不正確的策略選擇會導致三種系統性風險：

| 失敗條件 | 風險 | 症狀 |
|---------|------|------|
| 假設 injection 成功 = policy 遵守 | `false_allow` | 實際違規但 enforcement 未觸發 |
| observation 未耦合 enforcement | `false_confidence` | artifact 存在但決策未使用它 |
| capability 被高估（誤分 class） | `governance bypass` | 治理路徑比 agent 能力假設的更弱 |

失敗模型的主要使用場景：
- 新增 agent 時的 classification review checklist
- 定期 capability audit（agent 版本變更時重評）
- incident review（當 governance 被繞過時，定位根因）

---

## `governance_strategy` 欄位規格

這個欄位記錄本次 session 實際採用的治理路徑。

```
governance_strategy: "injection+enforcement"
                   | "minimal_injection+enforcement"
                   | "no_injection+strict_enforcement"
```

消費者：
- `session_end` artifact → reviewer 可見
- `decision_context` bridge → 下游 pre_task 可參考歷史策略
- trust signal dashboard → 顯示 session 級別治理強度

---

## `injection_reliance` 欄位規格

這個欄位記錄 enforcement 對 injection 的依賴程度。

```
injection_reliance: "none"    # enforcement 完全獨立，injection 是純輔助
                  | "partial" # enforcement 部分參考 injection 信號（需說明）
                  | "high"    # enforcement 依賴 injection 成功（架構警告）
```

**`high` 是警示狀態**，代表存在設計缺陷：任何讓 enforcement 依賴 injection 成功
的情況都應被標記並審查。

消費者：
- `post_task_check` → 若 `injection_reliance: high` 觸發 advisory warning
- reviewer surface → 顯示治理路徑的 injection 耦合風險

---

## 與現有 runtime 的對接

| 現有路徑 | 對應策略 | class |
|---------|---------|-------|
| `claude_code` adapter + CLAUDE.md | injection + enforcement | `instruction_capable` |
| `codex` adapter | minimal injection + enforcement | `instruction_limited` |
| `gemini` adapter | minimal injection + enforcement | `instruction_limited` |
| external API (no hooks) | no injection + artifact review | `wrapper_only` |
| human reviewer | n/a | 不適用 |

這個對照目前是 **推測性的（provisional）**，需要在各 adapter 的 harness
實際確認 capability profile 後才能成為正式分類。

---

## 邊界

這份文件不負責：
- 決定要注入哪些具體規則（見 `runtime-injection-layer-plan.md`）
- 定義 observation signal 的完整清單（見 `runtime-injection-observation-mapping.md`）
- enforcement hook 的實作細節（見 `runtime_hooks/`）

它只負責：
- 根據 capability 決定治理策略
- 定義 `governance_strategy` 與 `injection_reliance` 兩個可觀測欄位
- 提供失敗模型供 classification review 使用
