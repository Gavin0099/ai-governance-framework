# Trust Signal Dashboard

更新日期：2026-04-08

這一頁是 framework adoption 與 release-facing trust signal 的穩定入口。它的用途不是提供所有細節，而是讓你在同一頁先回答：

- quickstart 還能不能跑
- bundled example 是否仍健康
- release-facing 文件是否對齊
- governance self-audit 是否仍然過關
- external contract repo 是否仍維持預期的 enforcement posture

## 最快本地指令

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

如果想產生可分享的 dashboard-style 輸出：

```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml \
  --format markdown
```

## 生成 publication snapshot

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

如果要直接寫到穩定 docs path：

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

回讀 publication metadata：

```bash
python governance_tools/trust_signal_publication_reader.py \
  --file artifacts/trust-signals/PUBLICATION_MANIFEST.json \
  --format human
```

如果走 repo-local docs status：

```bash
python governance_tools/trust_signal_publication_reader.py \
  --project-root . \
  --docs-status \
  --format human
```

## 這頁在看什麼

目前這個 dashboard 最主要在看：

- framework 自己的 quickstart / readiness / audit 是否健康
- release-facing 文件是否仍與目前主線一致
- external contract repo 是否仍暴露預期的 cross-domain enforcement posture

它不是拿來宣告：

- full interception coverage 已完成
- 所有 domain validator 都是 hard-stop
- semantic verification 已達到 full policy engine 等級

這些邊界仍然應該保持可見。

## CI / generated artifacts

目前信號 bundle 會寫到：

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

當 external contract repo 有提供時，publication metadata 也會帶 compact 的 cross-domain enforcement summary。

## 相關頁面

- [Status Index](README.md)
- [Runtime Governance 狀態](runtime-governance-status.md)
- [Next Steps](next-steps.md)
- [Release Index](../releases/README.md)
- [Known Limits](../LIMITATIONS.md)
