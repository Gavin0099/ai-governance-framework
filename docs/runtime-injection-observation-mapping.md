# Runtime Injection Observation Mapping

> 更新日期：2026-04-09
> 定位：bounded mapping for consumption requirements and observable proxies

---

## 目的

這份文件定義：

```text
consumption requirement -> observable proxy -> interpretation boundary
```

它的目的是把 `runtime injection requirement` 與可觀測 proxy 對齊，讓 reviewer 能知道：

- 哪些 requirement 可以被哪些 proxy 部分回證
- 哪些 signal 只是 `observable compliance evidence`
- 哪些東西絕對不能被誤當成 compliance proof

---

## 核心邊界

這份 mapping **不是**：

- proof-of-compliance engine
- policy obedience detector
- generic runtime authority layer

它只做一件事：

> 把 bounded runtime injection requirement 和 bounded observation proxy 接起來，並把 interpretation boundary 寫清楚。

---

## Signal Classes

### 1. Environment Degradation Signals

這類 signal 描述的是：

- runtime state
- context quality
- visibility degradation

它們可以提高 reviewer 警覺，但不能直接被當成 behavioral non-compliance。

例子：

- `context_degraded`
- `required_evidence_missing`
- truncation / partial visibility 類 signal

### 2. Behavioral Compatibility Signals

這類 signal 是比較接近 requirement 的 execution proxy。

它們也仍然只是：

- `behavioral compatibility evidence`
- 不是 `proof_of_compliance`
- 不是 `proof_of_violation`

---

## First-Slice Requirements

目前 mapping 先只處理：

- `reread_before_edit`
- `require_full_read_for_large_files`

刻意不處理：

- `must understand policy`
- `must follow architecture rules`
- 任何需要推斷 agent 內在理解的 requirement

---

## Mapping Table

| Consumption requirement | Acceptable observation proxy | Non-proof caveat | Intended use |
|---|---|---|---|
| `reread_before_edit` | edited file 在 task window 內出現 read event | 無法證明 agent 真的理解 reread，也無法證明 reread 與 edit 的因果充分成立 | reviewer-visible warning / advisory escalation hint |
| `require_full_read_for_large_files` | large file 出現 chunked read / repeated read coverage，且無 truncation signal | 無法證明 relevant section coverage，也無法證明 retention | partial visibility / review risk advisory |
| `escalate_if_context_degraded` | `context_degraded` signal 出現 | 這是 environment state，不是 consumption proof | raise reviewer caution / escalate task posture |
| `escalate_if_required_evidence_missing` | `required_evidence_missing` signal 出現 | 這是 execution completeness signal，不是 behavioral proof | escalate / stop path 與 reviewer-visible evidence gap |

---

## Interpretation Boundary

這些 proxy 只能被渲染成：

- `observable compliance evidence`
- `behavioral compatibility signal`
- `reviewer-facing advisory substrate`

它們不能被渲染成：

- `proof_of_compliance`
- `proof_of_violation`
- `policy_fully_obeyed`

---

## Non-Equivalence Rules

必須明確避免以下誤推論：

- observed proxy present ≠ requirement satisfied
- observed proxy absent ≠ requirement violated
- single event ≠ behavioral compliance
- environment degradation ≠ behavioral failure

---

## First Executable Slice

目前第一個 executable slice 是：

- `require_full_read_for_large_files`

而且只以這種姿態存在：

- advisory-only executable proxy
- partial visibility / review risk hint
- 不改 verdict
- 不當成 `proof_of_compliance`
- 不當成 `proof_of_violation`

---

## 這份 mapping 的價值

這份文件的價值在於：

- 讓 `runtime injection snapshot` 與 observation 之間有 bounded 接點
- 讓 reviewer 不會把 proxy 誤讀成 generic warning 或過度解讀成 compliance proof
- 為 post-task / execution-time observation 留下更清楚的語義邊界

---

## Non-Goals

這份 mapping 不處理：

- generic compliance proof engine
- adapter-specific instrumentation matrix
- runtime hard gate
- semantic understanding detection
- machine-authoritative consumption scoring

---

## 一句話

`Runtime Injection Observation Mapping` 的目標，是讓 runtime injection requirement 對到 bounded、可觀測、不可濫用的 proxy，而不是把 proxy 升格成新的 compliance authority。
