# Trust Signal Dashboard

更新日期：2026-04-09

這份頁面整理 framework adoption 與 release-facing trust signal，供 reviewer 與 adopter 快速查看。當前預設展示版本以 `v1.1.0` 為 release-facing 基準；若要檢查其他版本，請搭配對應 release note 與 release readiness 指令使用。歷史版本 `v1.0.0-alpha` 仍可透過同一組 trust signal / release readiness 工具重現與審查。

它主要回答幾件事：
- quickstart 是否可跑
- bundled example 是否可驗
- release-facing trust surface 是否成立
- governance self-audit 是否可讀
- external contract repo 的 cross-domain enforcement posture 是否可被追蹤

## 核心指令

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

如果要看 dashboard-style 的 markdown：
```bash
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

若要把結果發布到 repo-local docs status path：
```bash
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

讀 publication metadata：
```bash
python governance_tools/trust_signal_publication_reader.py \
  --file artifacts/trust-signals/PUBLICATION_MANIFEST.json \
  --format human
```

讀 repo-local docs status：
```bash
python governance_tools/trust_signal_publication_reader.py \
  --project-root . \
  --docs-status \
  --format human
```

## Dashboard 的語義邊界

這份 dashboard 是 reviewer-facing 的 trust overview，不代表：
- full interception coverage
- 每個 domain validator 都已成為 hard-stop
- semantic verification 已等同 full policy engine

它是 bounded、release-facing 的 trust overview，可用於 `v1.1.0` 與 `v1.0.0-alpha` 這類已發版版本的回放與檢查。

## CI / Generated Artifacts

常見 trust-signal bundle 輸出包括：
- `artifacts/trust-signals/latest.txt`
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

對 external contract repo 來說，這些 publication metadata 會形成 compact 的 cross-domain enforcement summary。

## 相關頁面

- [Status Index](README.md)
- [Runtime Governance Status](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Next Steps](next-steps.md)
- [Release Index](../releases/README.md)
- [Known Limits](../LIMITATIONS.md)
