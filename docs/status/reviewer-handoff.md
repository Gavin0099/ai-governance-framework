# Reviewer Handoff 狀態

?湔?交?嚗?026-04-09

???Ｘ??reviewer ??repo 銝剜????閬???handoff surface??霈?reviewer 銝???蝧?trust?elease?untime status page嚗??賢翰?遣蝡?
- trust / adoption ?暹?
- release / package readiness
- runtime boundary ??current posture

摰??舀??authority layer嚗 reviewer-facing ??????
## ?敹怎??砍瑼Ｘ?賭誘

```bash
python governance_tools/reviewer_handoff_summary.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

??summary ????
- `trust_signal_overview.py`
- `release_surface_overview.py`

?拙?霈?reviewer ?典銝?亙敹恍遣蝡????
## ?Ｗ Reviewer Bundle

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --write-bundle artifacts/reviewer-handoff/v1.1.0 \
  --format human
```

霈??bundle嚗?
```bash
python governance_tools/reviewer_handoff_reader.py \
  --release-version v1.1.0 \
  --file artifacts/reviewer-handoff/v1.1.0/MANIFEST.json \
  --format human
```

霈??publication-layer summary嚗?
```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --release-version v1.1.0 \
  --file artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json \
  --format human
```

## 撖怠 Repo-Local Docs ???
```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --publish-docs-status \
  --format human
```

?嚗?
```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --project-root . \
  --release-version v1.1.0 \
  --docs-status \
  --format human
```

## ??Surface ??隞暻?
??surface ?身閮璅嚗?- 蝯?reviewer 銝隞賢?湔?梯???summary嚗??臬蝯?raw manifest
- ?? handoff-ready ?縑??摨?- ??trust?elease?untime posture 銋?撱箇?銝?餈質馱??reviewer ?亙

## 撱箄降??Reviewer 瘚?

1. ?? `reviewer_handoff_summary.py`
2. ?亥???trust / adoption ????? [Trust Signal Dashboard](trust-signal-dashboard.md)
3. ?亥???release / package / runtime 銝餌?嚗?霈 [Runtime Governance ??(runtime-governance-status.md)
4. ?亥???external domain ??enforcement posture嚗?霈 [Domain Enforcement Matrix](domain-enforcement-matrix.md)

## 撣貉? Artifact 頝臬?

??CI 撌脩??reviewer handoff bundle嚗虜閬楝敺??穿?

- `artifacts/reviewer-handoff/v1.1.0/latest.txt`
- `artifacts/reviewer-handoff/v1.1.0/latest.json`
- `artifacts/reviewer-handoff/v1.1.0/latest.md`
- `artifacts/reviewer-handoff/v1.1.0/INDEX.md`
- `artifacts/reviewer-handoff/v1.1.0/MANIFEST.json`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.md`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.json`
- `artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `artifacts/reviewer-handoff/PUBLICATION_INDEX.md`

?亙歇?郊??docs status嚗?銝?砌??潘?
- `docs/status/generated/reviewer-handoff/`

撣貉??亙嚗?- `docs/status/generated/reviewer-handoff/README.md`
- `docs/status/generated/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `docs/status/generated/reviewer-handoff/site/README.md`

## ?賊??

- [Status Index](README.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Runtime Governance ??(runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Release Index](../releases/README.md)
