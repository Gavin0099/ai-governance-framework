# Advisory Slice Boundary

## Purpose

這份文件定義目前 advisory slice 的第一階段完成邊界。

目的不是擴張 advisory 線，而是防止後續因為「還能再做」而把這條線誤判成未完成主線。

## What This Slice Now Demonstrates

目前 advisory slice 已經證明：

- advisory signal 已有明確 taxonomy
- advisory signal 已有 phase boundary
- advisory signal 已有最小 producer contract
- advisory metadata 已被至少一個 runtime consumer 轉成 reviewer-facing semantics
- 至少一個 signal 已在兩個 reviewer-visible、non-verdict-bearing surfaces 上維持語義一致

## Current Completed Scope

### Signal Scope

目前這一階段只明確處理三個 signal：

- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

### Consumer Scope

目前已成立的 consumer 僅限：

- `pre_task_check` human-readable surface
- `post_task_check` human-readable surface

這些 consumer 都屬於：

- reviewer-visible
- non-verdict-bearing
- non-machine-authoritative

### Cross-Surface Consistency Scope

目前已完成的跨-surface consistency 例子只有：

- `required_evidence_missing`

這代表 advisory semantics 已有第一個可遷移案例，但不代表所有 signal 已完成 full surface matrix 驗證。

## Done Boundary For This Phase

本階段可視為已達成暫停點，當以下條件成立：

- 至少有兩個真實 consumer
- 至少有一個跨-surface consistency example
- taxonomy / phase boundary / producer contract 都已存在
- advisory semantics 已被 reviewer-facing surface 消費，而不只是文件定義
- advisory signal 仍未被擴張成 verdict proof、machine authority、或 hard gate

## Explicit Non-Goals

本階段刻意不追求：

- full signal x full surface matrix
- machine-readable advisory authority expansion
- advisory-to-verdict coupling
- proof-bearing compliance signal
- generic runtime signal universe
- 因為有 proxy 就擴成 edit legitimacy gate

## Stop Rules

若沒有新的 consumer need 或新的誤讀風險，本條線應暫停，不為了延續進度而擴張：

- 不因為還有其他 signal 可搬到 post-task，就自動視為必做
- 不因為 metadata 已結構化，就自動接入 machine-facing artifact
- 不因為已有兩個 surfaces，就追求 full coverage completeness

## Next Move Gate

只有在以下情況，才建議重新打開這條 advisory 線：

- 出現第二個真正需要 advisory semantics 的 reviewer-visible surface
- 現有 rendering 被發現仍有誤讀風險
- 某個 signal 在 phase 切換時語義漂移
- downstream consumer 需要一致的 reviewer-facing advisory rendering

若未出現上述條件，應視為這一階段已收斂。
