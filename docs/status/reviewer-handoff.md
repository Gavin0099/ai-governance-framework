# Reviewer Handoff

更新日期：2026-04-09

這個頁面整理 reviewer 在 repo 中接手時最需要看的 handoff surface。目的是讓 reviewer 不必逐一翻 trust、release、runtime status page，也能快速建立：
- trust / adoption 現況
- release / package readiness
- runtime boundary 與 current posture

它不是新的 authority layer，而是 reviewer-facing 的聚合入口。

## 最快的本地檢查命令

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

適合讓 reviewer 用單一入口快速建立當前狀態。

## 產出 Reviewer Bundle

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --write-bundle artifacts/reviewer-handoff/v1.1.0 \
  --format human
```

讀取 bundle：

```bash
python governance_tools/reviewer_handoff_reader.py \
  --release-version v1.1.0 \
  --file artifacts/reviewer-handoff/v1.1.0/MANIFEST.json \
  --format human
```

讀取 publication-layer summary：

```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --release-version v1.1.0 \
  --file artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json \
  --format human
```

## 寫入 Repo-Local Docs 狀態

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --publish-docs-status \
  --format human
```

再用：

```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --project-root . \
  --release-version v1.1.0 \
  --docs-status \
  --format human
```

## 這個 Surface 提供什麼

這個 surface 的設計目標是：
- 給 reviewer 一份可直接閱讀的 summary，而不是只給 raw manifest
- 提供 handoff-ready 的信號密度
- 在 trust、release、runtime posture 之間建立一個可追蹤的 reviewer 入口

## 建議的 Reviewer 流程

1. 先跑 `reviewer_handoff_summary.py`
2. 若要看 trust / adoption 狀態，再讀 [Trust Signal Dashboard](trust-signal-dashboard.md)
3. 若要看 release / package / runtime 主線，再讀 [Runtime Governance 狀態](runtime-governance-status.md)
4. 若要看 external domain 的 enforcement posture，再讀 [Domain Enforcement Matrix](domain-enforcement-matrix.md)

## 常見 Artifact 路徑

若 CI 已產出 reviewer handoff bundle，常見路徑包括：

- `artifacts/reviewer-handoff/v1.1.0/latest.txt`
- `artifacts/reviewer-handoff/v1.1.0/latest.json`
- `artifacts/reviewer-handoff/v1.1.0/latest.md`
- `artifacts/reviewer-handoff/v1.1.0/INDEX.md`
- `artifacts/reviewer-handoff/v1.1.0/MANIFEST.json`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.md`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.json`
- `artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `artifacts/reviewer-handoff/PUBLICATION_INDEX.md`

若已同步到 docs status，則一般位於：
- `docs/status/generated/reviewer-handoff/`

常見入口：
- `docs/status/generated/reviewer-handoff/README.md`
- `docs/status/generated/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `docs/status/generated/reviewer-handoff/site/README.md`

## 相關頁面

- [Status Index](README.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Runtime Governance 狀態](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Release Index](../releases/README.md)
