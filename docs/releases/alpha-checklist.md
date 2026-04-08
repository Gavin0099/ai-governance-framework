# Alpha Release Checklist

更新日期：2026-04-08

目前追蹤的正式 release：`v1.1.0`

這份 checklist 刻意保持輕量。它的作用是把 release-facing trust signal 變成可 review 的顯性項，而不是散落在 CI、README 註記與零散 terminal output 中。

## Core Confidence Checks

- [x] `requirements.txt` 存在，且符合文件中的 local setup path
- [x] `start_session.md` 提供五分鐘可走通的 guided entry path
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

## Release-Facing Artifacts

- [x] `README.md` 已反映當前 release 定位
- [x] `CHANGELOG.md` 已連到 `docs/releases/v1.1.0.md`
- [x] `docs/releases/v1.1.0.md` 存在
- [x] `docs/releases/v1.1.0-github-release.md` 存在
- [x] `docs/releases/v1.1.0-publish-checklist.md` 存在
- [x] `docs/releases/v1.0.0-alpha.md` 存在（previous release）
- [x] `docs/releases/v1.0.0-alpha-github-release.md` 存在（previous release）
- [x] `docs/releases/v1.0.0-alpha-publish-checklist.md` 存在（previous release）
- [x] `docs/status/runtime-governance-status.md` 已反映當前 maturity
- [x] `docs/status/README.md` 已指向 generated status landing path
- [x] `docs/status/trust-signal-dashboard.md` 已說清 repo-local generated status path
- [x] `docs/releases/generated/README.md` 存在，可作 generated release-package 入口
- [x] `docs/LIMITATIONS.md` 有誠實描述當前邊界

## 要保持可見的已知邊界

- [x] interception coverage 仍是 partial，不是 fully closed
- [x] 多數 domain validation 仍是 advisory-first
- [x] semantic verification 仍淺於 full policy engine
- [x] rule classification 尚未按 repo type 分化
- [x] external domain seam 雖然真實存在，但還不是 versioned plugin marketplace
