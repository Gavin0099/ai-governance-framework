# Classification Evidence 語義：欄位意義與限制

## 目的

這份文件定義 `classification_evidence` 中各欄位的語義邊界。
它要回答三件事：

1. 每個 evidence field 代表什麼
2. 每個 evidence field **不代表**什麼
3. 哪些欄位屬於 presence evidence，哪些屬於 observation evidence

核心原則：

> classification 是 proxy-based governance classification，不是 capability truth model。

這些 evidence field 的用途，是讓 reviewer 與 runtime 知道這次 session 應採用哪種治理姿態，而不是證明 agent 的內在能力。

---

## 兩種 evidence 類型

| 類型 | 定義 | 不應被解讀成 |
|---|---|---|
| **Presence evidence** | 某個 surface 或 capability 是否存在的訊號 | 不能直接推論 agent 已理解或遵守規則 |
| **Observation evidence** | 某個 action / state 是否真的被觀測到 | 不等於 capability truth，仍需結合 presence 與邊界條件 |

---

## 各欄位語義

### `has_file_access`

代表：
- runtime process / hook script 觀測到 repo file I/O 能力存在

不代表：
- agent 已完整閱讀檔案
- 本次 session 已對相關檔案做出正確 read
- file access 本身可以替代 reviewer reconstruction

較接近的外部證據：
- `runtime_repo_access_observed`

### `instruction_loaded`

代表：
- instruction surface 有被載入到本次 session 的證據

不代表：
- agent 已理解 instruction
- agent 已正確遵守 instruction
- instruction 一定足以支撐治理正確性

較接近的外部證據：
- `instruction_surface_present`

### `context_integrity`

代表：
- runtime 已觀測到 affirmative degradation signal
- 或目前 context condition 足以讓 reviewer 合理懷疑完整性下降

不代表：
- `full` 就一定沒有風險
- token budget / truncation 一定已被完整量化
- context 完整就等於 decision 正確

補充：
- 缺少 affirmative degradation signal 時，通常維持 `full`
- 若證據不足，不應硬推成 `full`；可保留 `unknown`

### `tool_gate`

代表：
- session closeout boundary 或 task boundary 的 hook / gate 是否可見
- session 是否具備最低限度的 pre/post gating surface

不代表：
- agent 本身具有高能力
- 只要存在 hook 就代表 enforcement 完整
- tool gate 存在即可推論治理品質足夠

較接近的外部證據：
```text
session_boundary_observed: true
pre_task_hook_present: true
post_task_hook_present: true
```

---

## Evidence 組合原則

classification evidence 必須組合判讀，不應單欄位過度推論。

例子：
- `instruction_loaded=true` 只表示 instruction surface 出現，不能推論 policy 已被吸收
- `has_file_access=true` 只表示檔案存取能力存在，不能推論 relevant files 已被正確閱讀
- `tool_gate=active` 只表示 gating surface 可見，不能推論所有 enforcement 都已成功執行

---

## 與 classification 的關係

這些 evidence 最終會被 runtime 用來推導：
- `effective_agent_class`
- `governance_strategy`
- `injection_reliance`

但 evidence 本身不等於 classification 結果，也不等於最終的 reviewer judgment。

---

## 一句總結

`classification_evidence` 的用途，是為 session-level governance classification 提供可觀測 proxy；它幫助 runtime 做保守分類，但不構成 capability truth。
