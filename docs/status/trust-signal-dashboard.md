# Trust Signal Dashboard

?湔?交?嚗?026-04-09

?遢??渡? framework adoption ??release-facing trust signal嚗? reviewer ??adopter 敹恍???閮剖?蝷箇??砌誑 `v1.1.0` ??release-facing ?箸?嚗閬炎?亙隞??穿?隢????release note ??release readiness ?誘雿輻?風?脩???`v1.0.0-alpha` 隞????蝯?trust signal / release readiness 撌亙??祟?乓?
摰蜓閬?蝑嗾隞嗡?嚗?- quickstart ?臬?航?
- bundled example ?臬?舫?
- release-facing trust surface ?臬??
- governance self-audit ?臬?航?
- external contract repo ??cross-domain enforcement posture ?臬?航◤餈質馱

## ?詨??誘

```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --external-contract-repo D:/USB-Hub-Firmware-Architecture-Contract \
  --external-contract-repo D:/Kernel-Driver-Contract \
  --external-contract-repo D:/IC-Verification-Contract \
  --format human
```

憒?閬? dashboard-style ??markdown嚗?```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --format markdown
```

## Publication Snapshot

```bash
python governance_tools/trust_signal_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --external-contract-repo D:/USB-Hub-Firmware-Architecture-Contract \
  --external-contract-repo D:/Kernel-Driver-Contract \
  --external-contract-repo D:/IC-Verification-Contract \
  --write-bundle artifacts/trust-signals \
  --publish-status-dir artifacts/trust-signals/published \
  --format human
```

?亥????撣 repo-local docs status path嚗?```bash
python governance_tools/trust_signal_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --external-contract-repo D:/USB-Hub-Firmware-Architecture-Contract \
  --external-contract-repo D:/Kernel-Driver-Contract \
  --external-contract-repo D:/IC-Verification-Contract \
  --publish-docs-status \
  --format human
```

霈 publication metadata嚗?```bash
python governance_tools/trust_signal_publication_reader.py \
  --file artifacts/trust-signals/PUBLICATION_MANIFEST.json \
  --format human
```

霈 repo-local docs status嚗?```bash
python governance_tools/trust_signal_publication_reader.py \
  --project-root . \
  --docs-status \
  --format human
```

## Dashboard ??蝢拚???
?遢 dashboard ??reviewer-facing ??trust overview嚗?隞?”嚗?- full interception coverage
- 瘥?domain validator ?賢歇? hard-stop
- semantic verification 撌脩???full policy engine

摰 bounded?elease-facing ??trust overview嚗?冽 `v1.1.0` ??`v1.0.0-alpha` ??撌脩???祉???炎?乓?
## CI / Generated Artifacts

撣貉? trust-signal bundle 頛詨?嚗?- `artifacts/trust-signals/latest.txt`
- `artifacts/trust-signals/latest.json`
- `artifacts/trust-signals/latest.md`
- `artifacts/trust-signals/history/*`
- `artifacts/trust-signals/INDEX.md`
- `artifacts/trust-signals/MANIFEST.json`
- `artifacts/trust-signals/PUBLICATION_MANIFEST.json`
- `artifacts/trust-signals/PUBLICATION_INDEX.md`
- `artifacts/trust-signals/published/manifest.json`
- `artifacts/trust-signals/published/*`
- `artifacts/trust-signals/published/history/*`
- `artifacts/trust-signals/published/INDEX.md`

撠?external contract repo 靘牧嚗? publication metadata ?耦??compact ??cross-domain enforcement summary??
## ?賊??

- [Status Index](README.md)
- [Runtime Governance Status](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Next Steps](next-steps.md)
- [Release Index](../releases/README.md)
- [Known Limits](../LIMITATIONS.md)
