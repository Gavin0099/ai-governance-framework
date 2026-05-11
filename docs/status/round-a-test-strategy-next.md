# Round A Next Test Strategy

Date: 2026-05-11
Applies to: Copilot / Claude / ChatGPT lanes

## Goal

Validate **engineering outcome value**, not only behavior shaping quality.

## Test Layers

1. Data integrity layer (must pass first)
- summary/detail counters must match
- mapped session id must exist in runtime session index
- mapping confidence rules must be deterministic

2. Closure quality layer
- completion contract pass ratio
- native closeout ratio
- mapped high ratio

3. Outcome layer
- reviewer edit effort trend
- reopen/revert incidence
- integration stability trend

## Minimal Test Pack (recommended)

1. Cross-agent 3x3 comparable tasks
- docs consistency patch
- claim-boundary wording patch
- small cross-file sync patch

2. Hostile ambiguity pack (small)
- conflicting authority wording
- stale evidence reference
- ambiguous lifecycle phrasing

3. Ablation pack
- no governance vocabulary
- docs-only governance
- runtime-hooks only
- full governance contract

## Pass/Fail Guidance

Pass-ready for deeper rollout when all hold:
- data integrity checks pass without manual repair
- closure quality remains stable (>= target ratios)
- reviewer burden is stable or improving
- no evidence of drift masked by wording polish

Fail/hold when:
- summary/detail mismatch recurs
- native closure ratio drops under threshold
- reviewer burden rises without outcome gains

