# Runtime Injection Observation Mapping

> bounded mapping defined
> 更新日期：2026-04-09

## 目的

本文定義 consumption requirement → observable proxy → interpretation boundary 的有界映射：

```text
consumption requirement -> observable proxy -> interpretation boundary
```

本文**不**把 proxy 當作 compliance proof，核心主張：
- 任何 trigger / proxy 都不等同於 compliance proof
- 任何 environment degradation 都不等同於 behavioral failure

## 本文 mapping 的適用範圍

本文 mapping 適用於以下三個使用場景：
- 為每個 consumption requirement 提供可觀測的 observable proxy
- 把 proxy 結果轉為 `observable compliance evidence`
- 把 signal 結果輸出到 advisory / reviewer surface 供人工參閱

**不適用**：
- proof-of-compliance engine
- policy obedience detector
- generic runtime authority layer

## Signal Classes

### 1. Environment Degradation Signals

此類 signal 反映：
- runtime state
- context quality
- visibility degradation

此類 signal 應傳遞給 reviewer 供人工判斷，但**不代表 behavioral non-compliance**。
例如：
- `context_degraded`
- `required_evidence_missing`
- truncation / partial visibility 相關 signal

### 2. Behavioral Compliance Signals

此類 signal 反映：
- 有無合乎特定 proxy 要求的執行行為被記錄
- execution pattern 是否與 requirement 吻合

這類 signal 是「behavioral compatibility evidence」（非 proof）。

## First-Slice Requirements

本文 mapping 的初始優先 requirement：
- `reread_before_edit`
- `require_full_read_for_large_files`

**不在初始範圍**：
- `must understand policy`
- `must follow architecture rules`
- 任何依賴 agent 意圖判斷的 requirement

## Mapping Table

| Consumption requirement | Acceptable observation proxy | Non-proof caveat | Intended use |
|---|---|---|---|
| `reread_before_edit` | edited file 在同一 task window 中有 read event | 無法驗證 agent 是否真正依照 reread 的內容進行 edit，無法驗證 reread 是否在 edit 之前發生 | reviewer-visible warning / advisory escalation hint |
| `require_full_read_for_large_files` | large file 有 chunked read / repeated read coverage，且無 truncation signal | 無法驗證相關 section coverage，無法驗證 agent retention | partial visibility / review risk advisory |
| `escalate_if_context_degraded` | `context_degraded` signal 出現 | 只是 environment state，不是 consumption proof | raise reviewer caution / escalate task posture |
| `escalate_if_required_evidence_missing` | `required_evidence_missing` signal 出現 | 只是 execution completeness signal，不是 behavioral proof | escalate / stop path，把 reviewer-visible evidence gap 標出 |

## 合法的 interpretation boundary

以下是 proxy 結果可合法標記的：
- `observable compliance evidence`
- `behavioral compatibility signal`
- `reviewer-facing advisory substrate`

以下**不能**由 proxy 結果標記：
- `proof_of_compliance`
- `proof_of_violation`
- `policy_fully_obeyed`

## Non-Equivalence Rules

以下等號在本框架中一律不成立：
- observed proxy present ≠ requirement satisfied
- observed proxy absent ≠ requirement violated
- single event ≠ behavioral compliance
- environment degradation ≠ behavioral failure

## First Executable Slice

初始可執行 slice 只處理：
- `require_full_read_for_large_files`

此 slice 的性質：
- advisory-only executable proxy
- partial visibility / review risk hint
- 無 verdict
- 無法給出 `proof_of_compliance`
- 無法給出 `proof_of_violation`

## 本文 mapping 的維護邊界

- 若新增 `runtime injection snapshot` 的 observation 項目，需補充此文件的 bounded 說明
- 若 reviewer 要求使用 proxy 結果作為 generic warning，需澄清此處的 interpretation boundary
- 禁止把 post-task / execution-time observation 做成 non-human-reviewable 的自動裁決

## Non-Goals

本文 mapping 不包含：
- generic compliance proof engine
- adapter-specific instrumentation matrix
- runtime hard gate
- semantic understanding detection
- machine-authoritative consumption scoring

## 設計決定

本文定義的是：runtime injection requirement 的每個 bounded proxy 及其對應決定。proxy 本身**不具備** compliance authority。
