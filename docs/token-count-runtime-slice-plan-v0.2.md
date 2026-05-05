# Token Count Runtime Slice Plan v0.2

## Objective

在不破壞既有 governance 邊界下，補上 Token Count（數量）能力，並與 Token Trust（可信度）並排呈現，支援效率分析與 outcome 對照。

## Scope

### In Scope
- `codeburn_report.py`
- `test_codeburn_phase1_report.py`
- minimal runtime capture hook（單一 entry point，LLM client interceptor）

### Out of Scope
- `codeburn_analyze.py`
- DB schema migration（除非既有欄位已可承載）
- quality/compliance decision logic
- token-based automation for governance decisions

## Core Separation

```text
Token Count != Token Trust
Token Count != Governance Decision Signal
Token Trust != Authority Signal
```

## Normative Rules

### R1. Field Presence Contract

`token_count` 欄位必定存在；欄位內數值可為 `null`。

```yaml
token_count:
  prompt_tokens: int | null
  completion_tokens: int | null
  total_tokens: int | null
```

禁止為了「每次有數字」而假造 token。

### R2. Observability Classification

`token_observability_level` 由「粒度」判定，不由來源名稱判定：

- `none`
  - 無 token source，且無 token values
- `coarse`
  - estimated token
  - 或 provider 僅 request-level total usage
  - 或僅 aggregate token（無 step breakdown）
- `step_level`
  - 有 per-step token breakdown

`provider` 不自動等於 `step_level`。

### R3. Source Summary Classification

- `provider`
  - 所有 token values 均來自 provider usage
- `estimated`
  - 所有 token values 均來自估算
- `mixed`
  - 同一 report 同時存在 provider 與 estimated
- `unknown`
  - token values 缺失，或來源不可判定

### R4. Provenance Warning Policy

- `mixed_sources`
  - `token_source_summary = mixed`
- `provenance_unverified`
  - `token_source_summary = estimated`
  - 或 `token_source_summary = unknown`
  - 或缺少可驗證來源資訊
- `null`
  - provider-only 且無 mixed/unknown

### R5. Non-Authoritative Notice (MUST)

report 固定輸出以下文案（逐字）：

`Token fields are observational only and MUST NOT be used for automated decision, gating, or quality inference.`

## Dual-Gate Boundary Contract

### Governance Gate (semantic/quality/compliance)
- MUST NOT consume token fields
- `governance_decision_usage_allowed: false`（固定）

### Budget Gate (operational safety only)
- 本 slice 僅保留概念，不啟用 automated enforcement
- `operational_guard_usage_allowed: false`（固定）
- 成本熔斷/資源保護合約延後到獨立 Phase B 規格

## Minimal Runtime Capture Slice

採用單一 entry point 的 LLM client interceptor：

來源優先序：
1. provider usage（若存在）
2. estimated（fallback）
3. unknown（保守）

理由：
- 最小侵入，不改 analyze/decision boundary
- 來源最接近真實回應，易驗證
- 可向上擴展到 step-level，不推翻 Phase A

## Report Output Contract (Example)

```yaml
token_count:
  prompt_tokens: 640
  completion_tokens: 120
  total_tokens: 760

token_trust:
  token_source_summary: estimated
  token_observability_level: coarse
  provenance_warning: provenance_unverified
  governance_decision_usage_allowed: false
  operational_guard_usage_allowed: false
```

## Test Matrix (Minimum)

1. estimated token -> token_count present + observability `coarse`
2. provider token + step breakdown -> observability `step_level`
3. no token -> token_count structure present with nulls + `governance_decision_usage_allowed=false`
4. mixed sources -> count present + `mixed_sources` warning
5. provider total-only -> `coarse` (NOT `step_level`)
6. provider-only verified -> no provenance warning + governance usage remains false

## Rollout

1. 單一 repo 先導入（controlled exposure）
2. 觀察 1-2 週：
   - 是否被誤解為 quality signal
   - 是否有人誤以為 `operational_guard_usage_allowed=true`
   - 是否有人嘗試把 `token_count` 接入 automated enforcement
3. 再決定是否擴展至其他 repo

## Future Work (Out of Current Slice)

- Budget Guard Contract（獨立 Phase B）
- Trust-gated Budget Hard Stop policy
- operational enforcement telemetry and audit trail

## Exit Criteria

- report 穩定輸出 `token_count + token_trust + non-authoritative notice`
- 無 governance gate 誤用 token
- `operational_guard_usage_allowed` 在本 slice 維持 `false`
