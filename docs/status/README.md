# 狀態索引

更新日期：2026-04-09

本目錄是這個 repo 的 reviewer-facing 狀態入口，用來集中呈現 runtime、closeout、trust signal、coverage 與 handoff surface。它不是 generated artifact 的替代品，而是幫 reviewer 快速找到該看哪裡。

## 主要入口

- [Reviewer Handoff](reviewer-handoff.md)
  - reviewer-facing 的 handoff / summary surface
  - 適合在單次 review 或 session closeout 後快速理解狀態

- [Runtime Governance Status](runtime-governance-status.md)
  - 說明目前 runtime governance 主線的 bounded reality
  - 適合掌握 repo 的 maturity 與現行邊界

- [Closeout Audit](closeout-audit.md)
  - session workflow / canonical closeout 的 observation surface
  - 適合觀察 closeout valid rate、warning/none 比例與 audit flags

- [Trust Signal Dashboard](trust-signal-dashboard.md)
  - adoption / release-facing 的 trust signal 概覽
  - 適合查看 consuming repo、publication 與 trust snapshot 路徑

- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
  - external contract seam 與 domain enforcement posture 的對照頁
  - 適合查看各 domain 是否屬 advisory-first、mixed，或已有更強 enforcement

- [Runtime Surface Manifest](runtime-surface-manifest.md)
  - execution / evidence / authority surface 的 inventory 與 consistency signal

- [Execution Surface Coverage](execution-surface-coverage.md)
  - decision-aware coverage 的 bounded first slice

- [Next Steps](next-steps.md)
  - 目前主線後續順序與 bounded non-goals

## Generated 狀態入口

repo-local generated state 會落在 `docs/status/generated/`，常見入口包括：
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
