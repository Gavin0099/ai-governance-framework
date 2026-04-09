# Classification Evidence Semantics：classification evidence 代表什麼，不代表什麼

## 目的

這份文件定義 `classification_evidence` 裡各種 evidence field 的語義邊界。

它要回答三件事：

1. 每個 evidence field 到底在表達什麼
2. 每個 evidence field **不能**被解讀成什麼
3. 哪些欄位只屬於 presence evidence，哪些欄位比較接近 observation evidence

核心原則：

> classification 是 proxy-based governance classification，不是 capability truth model。

這些 evidence field 的任務，是幫 reviewer 看出 session 中有哪些治理 proxy 被觀測到，而不是證明 agent 真實能力。

---

## 兩種 evidence 類型

| 類型 | 定義 | 不能被解讀成 |
|---|---|---|
| **Presence evidence** | 某個 surface 或 capability 的外部存在訊號 | 不能直接推成語義上已被 agent 消化或正確使用 |
| **Observation evidence** | 某個 action / state 被真正觀測到的訊號 | 仍然不等於 capability truth，但比單純 presence 更強 |

---

## 主要 evidence 欄位

### `has_file_access`

它代表：

- runtime process / hook script 具有 repo file I/O 能力

它**不代表**：

- agent surface 本身已獲得 file access
- 該 session 中真的發生了對 repo 的有效 tool call
- 這個 agent 一定能穩定使用 file access

更準確的替代表述：

- `runtime_repo_access_observed`

### `instruction_loaded`

它代表：

- instruction surface 在 repo 中可被找到
- agent 至少面對過這個 instruction surface 的存在條件

它**不代表**：

- agent 已真正消化 instruction
- agent 已把 instruction 正確納入 context
- agent 的 interpretation 與 instruction 一致

更準確的替代表述：

- `instruction_surface_present`

### `context_integrity`

它代表：

- runtime 是否觀測到 affirmative degradation signal
- context condition 是否出現已知 degradation

它**不代表**：

- 沒有 degradation signal 就等於 `full`
- 沒有 warning 就等於 context 完整
- token budget / truncation 一定已被完全排除

因此：

- `full` 不應是預設值
- 預設較合理的是 `unknown`
- 只有在有正向 affirmative observation 時，才應收斂到 `full`

### `tool_gate`

它代表：

- session closeout boundary 是否可被 hook 觀測到
- session 是否至少在 closeout path 上具備可觀測 gating

它**不代表**：

- 整個 session 中每個 task 都被 pre/post gate 完整攔截
- pre_task hook / post_task hook 一定都存在
- agent 一定被完整治理

比較安全的拆法是：

```text
session_boundary_observed: true
pre_task_hook_observed: true | false | unknown
post_task_hook_observed: true | false | unknown
```

---

## 目前 posture

這些欄位都應被視為：

> proxy-based governance classification 的 evidence

也就是：

- 幫 reviewer 看 session 中有哪些治理 proxy 被觀測到
- 幫 reviewer 看有哪些 proxy 缺失或退化
- 幫 reviewer 避免把 availability / presence 誤讀成 capability truth

它們目前**不是**：

- `instruction_capable` 的真實能力證明
- `injection+enforcement` 已完全成立的證明
- `tool_gate: active` 就代表全流程受控的證明

---

## 與 transition / reaction 的關係

`classification_evidence` 主要回答的是 evidence 的語義邊界。  
如果 evidence 進一步造成 classification 變動，則應交由：

- `docs/classification-transition-semantics.md`
- `docs/classification-reaction-policy.md`

處理 transition 規則與 downstream reaction。
