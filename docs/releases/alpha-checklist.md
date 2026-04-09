# Alpha 發版信心檢查清單

更新日期：2026-04-09

這份清單用來確認 `v1.1.0` 發版前的基本信心是否成立。它不是宣告系統已成為完整 policy engine，而是確認目前這個 bounded runtime-governance release 可以被說明、檢查、重現與交付。

## 核心信心檢查

- [x] `requirements.txt` 可支撐本地安裝與啟動路徑
- [x] `start_session.md` 提供 guided entry path
- [x] `python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human`
- [x] `python governance_tools/example_readiness.py --format human`
- [x] `python governance_tools/release_readiness.py --version v1.1.0 --format human`
- [x] `python governance_tools/governance_auditor.py --project-root . --release-version v1.1.0 --format human`
- [x] `python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --format human`
- [x] `python governance_tools/trust_signal_snapshot.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --publish-docs-status --format human`
- [x] `python governance_tools/trust_signal_publication_reader.py --project-root . --docs-status --format human`
- [x] `python governance_tools/release_package_snapshot.py --version v1.1.0 --publish-docs-release --format human`
- [x] `python governance_tools/release_package_reader.py --version v1.1.0 --project-root . --docs-release --format human`
- [x] `python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human`
- [x] `python governance_tools/release_surface_overview.py --version v1.1.0 --format human`
- [x] `bash scripts/verify_phase_gates.sh`

## 對外發布面檢查

- [x] `README.md` 已能說明 release-facing 邊界
- [x] `CHANGELOG.md` 與 `docs/releases/v1.1.0.md` 對齊
- [x] `docs/releases/v1.1.0.md` 已就位
- [x] `docs/releases/v1.1.0-github-release.md` 已就位
- [x] `docs/releases/v1.1.0-publish-checklist.md` 已就位
- [x] `docs/releases/v1.0.0-alpha.md` 保留作為上一版 release 參照
- [x] `docs/releases/v1.0.0-alpha-github-release.md` 保留作為上一版 release 參照
- [x] `docs/releases/v1.0.0-alpha-publish-checklist.md` 保留作為上一版 release 參照
- [x] `docs/status/runtime-governance-status.md` 能反映目前 maturity 說法
- [x] `docs/status/README.md` 提供 generated status landing path
- [x] `docs/status/trust-signal-dashboard.md` 提供 repo-local generated status path
- [x] `docs/releases/generated/README.md` 提供 generated release-package 入口
- [x] `docs/LIMITATIONS.md` 明確說明目前能力邊界與不主張範圍

## 仍需誠實揭露的限制

- [x] workflow interception coverage 仍是 partial，不可宣稱 fully closed
- [x] domain validation / enforcement 仍以 advisory-first 為主，不可宣稱全面 hard-stop
- [x] semantic verification 仍不是 full policy engine
- [x] rule classification 仍依 repo type 與 rule pack 組合推定，不是完整語意理解
- [x] external domain seam 仍是 versioned contract / plugin marketplace 的前置形態
