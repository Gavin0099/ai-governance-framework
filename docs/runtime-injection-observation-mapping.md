# Runtime Injection Observation Mapping

## 目的

這份文件定義 `runtime injection snapshot` 與 `observation` 之間的最小對照邊界。

它不宣稱：
- 可以直接證明 agent 真的理解了 injected policy
- 可以直接證明 agent 內在遵守了所有 requirement

它只定義：
- 哪些 `consumption requirement` 可以被哪些 **observable proxy** 間接回證
- 哪些 signal 只是 environment degradation，不應被誤讀成 compliance proof
- 哪些 proxy 可以進一步成為 enforcement 可依賴的 input 候選

## Signal Class

這條線先明確分成兩類 signal，不混用。

### 1. Environment Degradation Signals

特性：
- 描述 runtime state / context quality
- 不等於 consumption proof
- 主要用於提高警戒、抬升 task level、或要求 escalation

例子：
- `context_degraded`
- `required_evidence_missing`
- `truncation_detected`

### 2. Behavioral Compliance Signals

特性：
- 描述 agent 外部可觀測行為是否與某 requirement 相容
- 不能直接證明內在理解
- 但可以作為 requirement 是否被滿足的 proxy

例子：
- edit 前是否有對應 read event
- large file 是否有足夠 read coverage
- edit 後是否有 validation step

## 最小 Mapping 原則

第一版只處理兩種 requirement：
- `reread_before_edit`
- `require_full_read_for_large_files`

選這兩條的原因：
- 比 `must follow architecture rules` 更可觀測
- 比 `must understand policy` 更不抽象
- 可以讓 consumption observation 與 execution observation 開始真正接起來

## Mapping Table

| Consumption requirement | Acceptable observation proxy | Non-proof caveat | Intended enforcement use |
|---|---|---|---|
| `reread_before_edit` | edited file 在當前 task window 內存在對應 read event | 無法證明 agent 真的理解內容，只能證明它有重新接觸檔案 | 缺失時可 `escalate` 或要求 reviewer 注意 |
| `require_full_read_for_large_files` | 超過門檻的大檔案存在 chunked read / repeated read coverage，且沒有 truncation signal | 無法證明 attention retention，只能證明 external read coverage 與 requirement 相容 | coverage 不足時可 `escalate` 或標示 `partial` |
| `escalate_if_context_degraded` | `context_degraded` signal 存在 | 這是 environment state，不是 compliance proof | raise minimum task level / escalate |
| `escalate_if_required_evidence_missing` | `required_evidence_missing` signal 存在 | 這是 execution completeness 問題，不是 consumption proof | escalate / stop |

## First Slice Decision

第一刀只做兩件事：

1. 明確區分：
- environment degradation
- behavioral compliance

2. 對這兩個 requirement 給出最小可用 proxy：
- `reread_before_edit`
- `require_full_read_for_large_files`

第一刀不做：
- generic proof-of-compliance engine
- semantic understanding detection
- adapter-specific instrumentation
- runtime hard gate

## Enforcement Posture

這些 proxy 第一版只應被視為：
- `observable compliance evidence`
- `behavioral compatibility signal`

不應被寫成：
- `proof_of_compliance`
- `policy_fully_obeyed`

也就是說，第一版的語意是：

> 某些外部可觀測行為，與 injected requirement 相容或不相容。

不是：

> 已經證明 agent 內在遵守了治理要求。

## 下一步候選

如果這份 mapping 被接受，下一步才適合做一個更小的 executable slice：

1. 先產一個 machine-readable mapping artifact
2. 再決定由哪個 runtime hook 消費
3. 優先接 reviewer-facing / advisory surface
4. 不直接升成 hard gate

## 成功標準

這份 mapping 成功的標準不是 coverage 變多，而是：

1. `trigger` 與 `consumption proof` 不再混淆
2. environment state 與 behavioral compliance 被正式切開
3. 至少兩個 requirement 有明確、可解釋、可保留 caveat 的 observable proxy
4. 後續 runtime implementation 不會把不可觀測的內在遵守誤寫成已驗證事實
