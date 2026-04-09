# Trust Signal Dashboard

更新日期：2026-04-09

這個頁面整理 framework adoption 與 release-facing trust signal 的主要觀測面，讓 reviewer 或 adopter 不必逐一手動比對 terminal output、artifact bundle、與零散狀態頁。

它回答的核心問題是：
- quickstart 是否可走通
- bundled example 是否可驗證
- release-facing trust surface 是否已形成
- governance self-audit 是否有顯著異常
- external contract repo 是否能提供 cross-domain enforcement posture

## 最快的本地檢查命令

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

若想要 dashboard-style 的 markdown 輸出：

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

若要直接寫入 repo-local docs status path：

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

讀取 publication metadata：

```bash
python governance_tools/trust_signal_publication_reader.py \
  --file artifacts/trust-signals/PUBLICATION_MANIFEST.json \
  --format human
```

讀取 repo-local docs status：

```bash
python governance_tools/trust_signal_publication_reader.py \
  --project-root . \
  --docs-status \
  --format human
```

## 這個 Dashboard 看什麼

這個 dashboard 的目的，是把以下幾條線收成同一個 reviewer-facing 面：
- framework 自身的 quickstart / readiness / audit 狀態
- release-facing trust surface 是否能被讀出
- external contract repo 是否能提供最低限度的 cross-domain enforcement posture

它不代表：
- full interception coverage 已完成
- 所有 domain validator 都已進 hard-stop
- semantic verification 已達 full policy engine

它提供的是 bounded、release-facing 的 trust overview。

## CI / Generated Artifacts

若已產出 trust-signal bundle，常見落點包括：

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

若有 external contract repo，一般 publication metadata 也會帶 compact 的 cross-domain enforcement summary。

## 相關頁面

- [Status Index](README.md)
- [Runtime Governance 狀態](runtime-governance-status.md)
- [Next Steps](next-steps.md)
- [Release Index](../releases/README.md)
- [Known Limits](../LIMITATIONS.md)
