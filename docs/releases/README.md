# Release Index

更新日期：2026-04-08

這個目錄是 `ai-governance-framework` 對外 release artifact 的穩定入口。它的作用不是取代 changelog，而是讓你快速找到：

- 目前正式 release 是哪一版
- 該版的 release note / GitHub release 草稿 / publish checklist
- generated release-package 的穩定讀取入口

## 當前正式 release

目前最後一個正式對外 release 仍是：

- [v1.1.0](v1.1.0.md)
- [GitHub Release Draft](v1.1.0-github-release.md)
- [Publish Checklist](v1.1.0-publish-checklist.md)
- [Alpha Checklist](alpha-checklist.md)

注意：

- 這裡是正式 release-facing 狀態
- `main` 分支上之後新增的 runtime / closeout / advisory / adoption hardening，不等於已重新發版

## 舊版 release

- [v1.0.0-alpha](v1.0.0-alpha.md)
- [v1.0.0-alpha GitHub Release Draft](v1.0.0-alpha-github-release.md)
- [v1.0.0-alpha Publish Checklist](v1.0.0-alpha-publish-checklist.md)

## Generated Release Package

generated release-package 的 repo-local 穩定入口在：

- [Generated Release Root](generated/README.md)

常用指令：

```bash
python governance_tools/release_package_snapshot.py --version v1.1.0 --publish-docs-release --format human
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
python governance_tools/release_surface_overview.py --version v1.1.0 --format human
```

## 建議搭配閱讀

- [Status Index](../status/README.md)
- [Runtime Governance 狀態](../status/runtime-governance-status.md)
- [Trust Signal Dashboard](../status/trust-signal-dashboard.md)
- [README](../../README.md)
