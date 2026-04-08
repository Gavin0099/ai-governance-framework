# Runtime Injection Observation Mapping

> 狀態：bounded mapping defined
> 更新日期：2026-04-08

## Purpose

這份文件的目的不是證明 agent 已遵守 injected policy，而是把：

```text
consumption requirement -> observable proxy -> interpretation boundary
```

這條線先寫清楚。

它要防止兩種常見誤判：

- 把 trigger / proxy 誤當成 compliance proof
- 把 environment degradation 誤當成 behavioral failure

## What This Mapping Is

這份 mapping 只處理：

- 哪些 consumption requirement 可以被某些 observable proxy 間接回證
- 哪些 proxy 只能算 `observable compliance evidence`
- 哪些 signal 只能進 advisory / reviewer surface

它不是：

- proof-of-compliance engine
- policy obedience detector
- generic runtime authority layer

## Signal Classes

### 1. Environment Degradation Signals

這類 signal 描述的是：

- runtime state
- context quality
- visibility degradation

它們可以提高警戒、抬高 reviewer 注意力，但不應被解讀成 behavioral non-compliance。

例子：

- `context_degraded`
- `required_evidence_missing`
- truncation / partial visibility 類 signal

### 2. Behavioral Compliance Signals

這類 signal 描述的是：

- 某些可觀測行為與 requirement 的相容程度
- execution pattern 是否與 requirement 比較一致

它們也不能直接當成 proof，只能當成 behavioral compatibility evidence。

## First-Slice Requirements

目前這份 mapping 只正式處理兩個 requirement：

- `reread_before_edit`
- `require_full_read_for_large_files`

刻意不處理：

- `must understand policy`
- `must follow architecture rules`
- 其他需要推定 agent 內在理解的 requirement

## Mapping Table

| Consumption requirement | Acceptable observation proxy | Non-proof caveat | Intended use |
|---|---|---|---|
| `reread_before_edit` | edited file 在當前 task window 之前有對應 read event | 不能證明 agent 真的理解了 reread 內容，也不能證明 reread 與 edit 的關聯足夠強 | reviewer-visible warning / advisory escalation hint |
| `require_full_read_for_large_files` | large file 被修改前出現 chunked read / repeated read coverage，且無 truncation signal | 不能證明 relevant section coverage，也不能證明 agent retention 充分 | partial visibility / review risk advisory |
| `escalate_if_context_degraded` | `context_degraded` signal 存在 | 這是 environment state，不是 consumption proof | raise reviewer caution / escalate task posture |
| `escalate_if_required_evidence_missing` | `required_evidence_missing` signal 存在 | 這是 execution completeness signal，不是 behavioral proof | escalate / stop path，或 reviewer-visible evidence gap |

## Current Interpretation Boundary

目前所有 proxy 都應被讀成：

- `observable compliance evidence`
- `behavioral compatibility signal`
- `reviewer-facing advisory substrate`

明確不是：

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

目前已落地的 executable slice 是：

- `require_full_read_for_large_files`

它的定位是：

- advisory-only executable proxy
- partial visibility / review risk hint
- 不改 verdict
- 不當成 proof_of_compliance
- 不當成 proof_of_violation

## What This Enables

這份 mapping 的價值在於：

- 把 `runtime injection snapshot` 與 observation 用同一套 bounded語義接起來
- 讓 reviewer 能看懂 proxy 是什麼，不是 generic warning
- 為未來的 post-task / execution-time observation 預留乾淨入口

## Non-Goals

這份 mapping 不做：

- generic compliance proof engine
- adapter-specific instrumentation matrix
- runtime hard gate
- semantic understanding detection
- machine-authoritative consumption scoring

## One-Line Summary

這份文件固定的是：  
runtime injection 的 requirement 可以被 bounded proxy 觀測，但這些 proxy 只能改善理解與審查，不足以單獨成立裁決權。
