# Decision Context Bridge

> 狀態：context bridge defined
> 更新日期：2026-04-08

## Purpose

這份文件的目的不是新增一套 verdict rule engine，而是把已存在的 integrity signals 正式綁到 decision artifact 上，形成可讀的 `decision_context`。

它處理的不是：

- verdict 是什麼

而是：

- 這個 verdict 是在什麼完整度條件下成立

## Why This Bridge Exists

本 repo 已經有兩條系統：

### 1. Decision System

- verdict
- trace
- DBL / pre_task / post_task
- reviewer handoff

### 2. Integrity Signal System

- runtime surface manifest
- execution coverage
- memory schema / sync signals
- advisory observations

如果這兩條線不綁起來，就會出現：

- decision 顯示 `ok`
- 但 execution coverage 可能不完整
- memory integrity 可能 partial
- reviewer 不知道這個 decision 是在什麼品質條件下做出的

## Bridge Shape

第一版 bridge 採用最小欄位：

```json
"decision_context": {
  "surface_validity": "complete | partial | unknown",
  "coverage_completeness": "complete | partial | missing",
  "memory_integrity": "complete | partial | not_applicable"
}
```

這些欄位的定位是：

- context
- not verdict
- not policy
- not authority

## Context Fields

### 1. `surface_validity`

回答：

- decision 所依賴的 execution / evidence surface 是否完整、是否有 mismatch

目前主要對應 signal：

- `unknown_surfaces`
- `orphan_surfaces`
- `evidence_surface_mismatch`

### 2. `coverage_completeness`

回答：

- 某個 decision 是否在可接受的 execution coverage 條件下成立

目前主要對應 signal：

- `missing_hard_required`
- `missing_soft_required`
- `dead_never_observed`
- `dead_never_required`

### 3. `memory_integrity`

回答：

- repo memory / host-agent memory / sync semantics 是否處於可接受狀態

目前主要對應 signal：

- `memory_sync_missing`
- `host_memory_not_applicable`
- `repo_memory_written_only`
- `memory_schema_status`

## Mapping Direction

這一層刻意不用 numeric scoring，只做 bounded mapping。

### `surface_validity`

- `complete`
  - 沒有 unknown / orphan / evidence mismatch
- `partial`
  - 有 signal，但尚未完全失效
- `unknown`
  - 連 manifest / consistency 本身都無法可靠提供

### `coverage_completeness`

- `complete`
  - 沒有 missing hard/soft requirement，且沒有 dead surface signal
- `partial`
  - 有 coverage 缺口，但仍有 bounded interpretation
- `missing`
  - coverage model 或 required surface 根本無法提供

### `memory_integrity`

- `complete`
  - memory schema 完整，且沒有 required sync 缺失
- `partial`
  - schema partial、repo-only、或 sync 有缺口
- `not_applicable`
  - 這次 decision 本來就不應要求 host memory sync

## Consumers

這一層第一批 consumer 應該是：

- reviewer
- session summary reader
- agent adoption baseline
- run record / handoff reader

目前刻意不直接給：

- runtime stop/pass authority
- policy precedence override
- hard gate

## Current Embedding Points

目前 `decision_context` 已接到：

- runtime verdict / trace artifact
- session_end summary
- reviewer-facing baseline / run record surfaces

它的作用是：

- 幫 reviewer 理解 decision validity
- 讓 baseline 不只看 raw signal，而能看 decision 所處條件

## Non-Goals

這份 bridge 不做：

- trust score
- numeric confidence score
- automatic verdict downgrade
- runtime hard gate
- policy override

## Success Condition

這一層成功的標準不是「它更聰明」，而是：

- reviewer 能看出 decision 的完整度上下文
- adoption / run baseline 能把 integrity signal 轉成可解釋的判讀面
- decision artifact 不再只顯示結果，也顯示 bounded validity context

## One-Line Summary

這份 bridge 的作用是：  
不是讓 signal 直接改 verdict，而是讓 verdict 不再脫離它所依賴的完整度條件。
