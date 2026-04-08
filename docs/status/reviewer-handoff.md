# Reviewer Handoff

更新日期：2026-04-08

這一頁是 reviewer 進 repo 時最上層的 handoff 入口。它的目的不是取代所有 trust / release / runtime status page，而是提供一個先看整體、再決定往哪個 surface 深挖的入口。

適合在你還不想先決定下一步是看：

- trust / adoption 健康度
- release / package readiness
- 或兩者和 runtime boundary 的關係

時先讀這頁。

## 最快本地指令

```bash
python governance_tools/reviewer_handoff_summary.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

這個 summary 會聚合：

- `trust_signal_overview.py`
- `release_surface_overview.py`

所以第一輪 reviewer 不需要先在兩個工具家族之間切換。

## 如果要保留成可回讀 bundle

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --write-bundle artifacts/reviewer-handoff/v1.1.0 \
  --format human
```

回讀生成 bundle：

```bash
python governance_tools/reviewer_handoff_reader.py \
  --release-version v1.1.0 \
  --file artifacts/reviewer-handoff/v1.1.0/MANIFEST.json \
  --format human
```

如果要看 publication-layer summary：

```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --release-version v1.1.0 \
  --file artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json \
  --format human
```

## 如果要發布到穩定 docs 路徑

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --publish-docs-status \
  --format human
```

之後可用：

```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --project-root . \
  --release-version v1.1.0 \
  --docs-status \
  --format human
```

## 何時先看這頁

先看這頁的情境：

- 想要一份 reviewer-facing summary，而不是先讀多份 raw manifest
- 想快速知道目前 handoff-ready 程度
- 想先辨識問題比較偏 trust、release，還是 runtime posture

## 建議閱讀順序

1. 先跑 `reviewer_handoff_summary.py`
2. 如果問題偏 trust / adoption，轉去 [Trust Signal Dashboard](trust-signal-dashboard.md)
3. 如果問題偏 release / package / runtime 邊界，轉去 [Runtime Governance 狀態](runtime-governance-status.md)
4. 如果要看 external domain 的 enforcement posture，轉去 [Domain Enforcement Matrix](domain-enforcement-matrix.md)

## 產物路徑

CI 或本地 bundle 目前會落在：

- `artifacts/reviewer-handoff/v1.1.0/latest.txt`
- `artifacts/reviewer-handoff/v1.1.0/latest.json`
- `artifacts/reviewer-handoff/v1.1.0/latest.md`
- `artifacts/reviewer-handoff/v1.1.0/INDEX.md`
- `artifacts/reviewer-handoff/v1.1.0/MANIFEST.json`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.md`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.json`
- `artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `artifacts/reviewer-handoff/PUBLICATION_INDEX.md`

穩定 docs 路徑則是：

- `docs/status/generated/reviewer-handoff/`

主要入口：

- `docs/status/generated/reviewer-handoff/README.md`
- `docs/status/generated/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `docs/status/generated/reviewer-handoff/site/README.md`

## 相關頁面

- [Status Index](README.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Runtime Governance 狀態](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Release Index](../releases/README.md)
