# 狀態入口

更新日期：2026-04-10

這個目錄收的是 repo 的 reviewer-facing 狀態頁。它們的目的不是取代 generated artifact，而是把 runtime reliability layer、closeout、trust signal、coverage、handoff 等 surface 整理成 reviewer 可讀的入口。

名詞說明：
- 對外主敘事使用 `runtime reliability layer`
- `governance` 保留為既有文件/工具相容名詞

## 主要入口

- [Reviewer Handoff](reviewer-handoff.md)
  - reviewer-facing handoff / summary surface
  - 用來看 reviewer 在接手時需要的最小治理上下文

- [Runtime Reliability Layer Status](runtime-governance-status.md)
  - 說明 repo 目前的 bounded runtime reality
  - 用來避免把 repo 誤讀成 full platform

- [AI Runtime Systems Positioning](ai-runtime-systems-positioning-2026-05-14.md)
  - 系統理論定位聲明（bounded nondeterminism / deterministic execution envelope）
  - 用來統一對外敘事邊界與非目標

- [Runtime Reliability Evidence Layer v0.1](runtime-reliability-evidence-layer-v0.1-2026-05-14.md)
  - observation-only runtime evidence substrate（明確禁止 gate 消費）
  - 用來定義 incident/recovery/side-effect/determinism 四類日志的語義邊界

- [Closeout Audit](closeout-audit.md)
  - session workflow / canonical closeout 的 observation surface
  - 用來看 closeout valid rate、warning/none 比例與 audit flags

- [Trust Signal Dashboard](trust-signal-dashboard.md)
  - adoption / release-facing 的 trust signal 摘要
  - 用來看 consuming repo、publication、status 之間的信號一致性

- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
  - external contract seam 的 enforcement posture 對照表
  - 用來看各 domain 是 advisory-first、mixed 還是較強 enforcement

- [Runtime Surface Manifest](runtime-surface-manifest.md)
  - execution / evidence / authority surface 的 inventory 與 consistency signal

- [Execution Surface Coverage](execution-surface-coverage.md)
  - decision-aware coverage 的 bounded first slice

- [Next Steps](next-steps.md)
  - bounded runtime reality 下的下一步順序與 non-goals

## Generated 入口

repo-local generated state 位於 `docs/status/generated/`，包括：

- `generated/runtime-surface-manifest.json`
- `generated/execution-surface-coverage.json`
- `generated/closeout-audit.json`
- `generated/README.md`
- `generated/PUBLICATION_INDEX.md`
- `generated/site/README.md`

## 建議閱讀順序

1. [Runtime Reliability Layer Status](runtime-governance-status.md)
2. [AI Runtime Systems Positioning](ai-runtime-systems-positioning-2026-05-14.md)
3. [Runtime Reliability Evidence Layer v0.1](runtime-reliability-evidence-layer-v0.1-2026-05-14.md)
4. [Closeout Audit](closeout-audit.md)
5. [Reviewer Handoff](reviewer-handoff.md)
6. [Domain Enforcement Matrix](domain-enforcement-matrix.md)
7. [Runtime Surface Manifest](runtime-surface-manifest.md)
8. [Execution Surface Coverage](execution-surface-coverage.md)
9. [Trust Signal Dashboard](trust-signal-dashboard.md)
10. [Next Steps](next-steps.md)
