# 狀態入口

更新日期：2026-04-10

這個目錄收的是 repo 的 reviewer-facing 狀態頁。它們的目的不是取代 generated artifact，而是把 runtime、closeout、trust signal、coverage、handoff 等 surface 整理成 reviewer 可讀的入口。

## 主要入口

- [Reviewer Handoff](reviewer-handoff.md)
  - reviewer-facing handoff / summary surface
  - 用來看 reviewer 在接手時需要的最小治理上下文

- [Runtime Governance Status](runtime-governance-status.md)
  - 說明 repo 目前的 bounded runtime reality
  - 用來避免把 repo 誤讀成 full platform

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

1. [Runtime Governance Status](runtime-governance-status.md)
2. [Closeout Audit](closeout-audit.md)
3. [Reviewer Handoff](reviewer-handoff.md)
4. [Domain Enforcement Matrix](domain-enforcement-matrix.md)
5. [Runtime Surface Manifest](runtime-surface-manifest.md)
6. [Execution Surface Coverage](execution-surface-coverage.md)
7. [Trust Signal Dashboard](trust-signal-dashboard.md)
8. [Next Steps](next-steps.md)
