# 狀態索引

更新日期：2026-04-08

本目錄收納的是這個 repo 對外或對 reviewer 可讀的穩定狀態頁。它的用途不是取代原始 artifact，而是提供較低成本的入口，讓人知道目前 runtime、closeout、trust signal 與後續方向各自停在哪裡。

## 主要入口

- [Reviewer Handoff](reviewer-handoff.md)
  - reviewer-facing 的高階交接頁
  - 適合先看整體 handoff，再往下鑽較細的 status surface

- [Runtime Governance Status](runtime-governance-status.md)
  - 目前最值得優先閱讀的主敘事頁
  - 說明 repo 現在的 bounded runtime reality、已完成能力，以及刻意不擴張的邊界

- [Closeout Audit](closeout-audit.md)
  - session workflow / canonical closeout 的 observation surface
  - 適合用來看 closeout valid rate、warning/none 分布與 audit flags

- [Trust Signal Dashboard](trust-signal-dashboard.md)
  - 對 adoption 與 release-facing trust signal 的快速總覽
  - 適合看目前 consuming repo / publication / trust snapshot 的外部狀態

- [Runtime Surface Manifest](runtime-surface-manifest.md)
  - execution / evidence / authority surface 的 inventory 與 consistency signal 狀態
  - 適合確認 runtime surface 是否完整、是否有 unknown/orphan/mismatch

- [Execution Surface Coverage](execution-surface-coverage.md)
  - decision-aware coverage 的 bounded first slice
  - 適合看 required/optional surface 是否缺失，與 dead surface 是否出現

- [Next Steps](next-steps.md)
  - 接下來最值得做的事
  - 用於收斂方向，而不是重述已完成內容

## 生成型狀態輸出

以下頁面或 JSON 由 status / audit tooling 生成，適合在想快速確認目前 generated state 時閱讀：

- `generated/runtime-surface-manifest.json`
- `generated/execution-surface-coverage.json`
- `generated/closeout-audit.json`

若要讀 generated root 的其他 publication-style 狀態，也可以再看：

- `generated/README.md`
- `generated/PUBLICATION_INDEX.md`

## 建議閱讀順序

1. 先看 [Runtime Governance Status](runtime-governance-status.md)
2. 再看 [Closeout Audit](closeout-audit.md)
3. 再看 [Reviewer Handoff](reviewer-handoff.md)
4. 若要看 runtime surface，讀 [Runtime Surface Manifest](runtime-surface-manifest.md)
5. 若要看 decision-aware completeness，讀 [Execution Surface Coverage](execution-surface-coverage.md)
6. 若要看 external adoption / release-facing trust 狀態，讀 [Trust Signal Dashboard](trust-signal-dashboard.md)
7. 若要看後續方向，最後讀 [Next Steps](next-steps.md)
