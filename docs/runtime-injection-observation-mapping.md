# Runtime Injection Observation Mapping

> bounded mapping defined
> 更新日期：2026-04-09

## 目的

這份文件把 consumption requirement 與 observable proxy 的關係寫清楚：

```text
consumption requirement -> observable proxy -> interpretation boundary
```

它的重點不是把 proxy 變成 compliance proof，而是把下列邊界寫死：
- 不把 trigger / proxy 當成 compliance proof
- 不把 environment degradation 當成 behavioral failure

## 這份 mapping 是什麼

這份 mapping 只做三件事：
- 定義 consumption requirement 可以對應哪些 observable proxy
- 明講 proxy 只能算 `observable compliance evidence`
- 讓 signal 能在 advisory / reviewer surface 中被使用

它不是：
- proof-of-compliance engine
- policy obedience detector
- generic runtime authority layer

## Signal Classes

### 1. Environment Degradation Signals

這類 signal 表示：
- runtime state
- context quality
- visibility degradation

這些 signal 可以提高 reviewer 警戒，但不能被解讀成 behavioral non-compliance。

例子：
- `context_degraded`
- `required_evidence_missing`
- truncation / partial visibility 類 signal

### 2. Behavioral Compliance Signals

這類 signal 表示：
- 某些可觀測行為與 requirement 是否相容
- execution pattern 是否與 requirement 衝突

它們也不等於 proof，而只是 behavioral compatibility evidence。

## First-Slice Requirements

目前這份 mapping 只處理兩個 requirement：
- `reread_before_edit`
- `require_full_read_for_large_files`

不處理：
- `must understand policy`
- `must follow architecture rules`
- 任何依賴 agent 內在理解的 requirement

## Mapping Table

| Consumption requirement | Acceptable observation proxy | Non-proof caveat | Intended use |
|---|---|---|---|
| `reread_before_edit` | edited file 在同一個 task window 內有 read event | 不能證明 agent 是否真的理解 reread 內容，也不能證明 reread 和 edit 的關聯足夠強 | reviewer-visible warning / advisory escalation hint |
| `require_full_read_for_large_files` | large file 有足夠 chunked read / repeated read coverage，且無 truncation signal | 不能證明有 relevant section coverage，也不能證明 agent retention | partial visibility / review risk advisory |
| `escalate_if_context_degraded` | `context_degraded` signal 成立 | 這是 environment state，不是 consumption proof | raise reviewer caution / escalate task posture |
| `escalate_if_required_evidence_missing` | `required_evidence_missing` signal 成立 | 這是 execution completeness signal，不是 behavioral proof | escalate / stop path，並提供 reviewer-visible evidence gap |

## 當前 interpretation boundary

目前這些 proxy 只能被視為：
- `observable compliance evidence`
- `behavioral compatibility signal`
- `reviewer-facing advisory substrate`

不能被視為：
- `proof_of_compliance`
- `proof_of_violation`
- `policy_fully_obeyed`

## Non-Equivalence Rules

以下推論一律禁止：
- observed proxy present ≠ requirement satisfied
- observed proxy absent ≠ requirement violated
- single event ≠ behavioral compliance
- environment degradation ≠ behavioral failure

## First Executable Slice

目前第一個 executable slice 是：
- `require_full_read_for_large_files`

它的定位是：
- advisory-only executable proxy
- partial visibility / review risk hint
- 不改 verdict
- 不作為 proof_of_compliance
- 不作為 proof_of_violation

## 這份 mapping 帶來什麼

- 讓 `runtime injection snapshot` 與 observation 有第一個 bounded 對接
- 讓 reviewer 能看出 proxy 的實際邊界，而不是 generic warning
- 為 post-task / execution-time observation 留下乾淨的演進路徑

## Non-Goals

這份 mapping 不做：
- generic compliance proof engine
- adapter-specific instrumentation matrix
- runtime hard gate
- semantic understanding detection
- machine-authoritative consumption scoring

## 一句話總結

這份文件做的事是：把 runtime injection requirement 能被哪些 bounded proxy 回證說清楚，但不把那些 proxy 假裝成 compliance authority。
