# 發版索引

更新日期：2026-07-27

本目錄收錄 `ai-governance-framework` 的正式發版文件、GitHub Release 草稿、發版檢查清單，以及本地產生的 release package 入口。

## 目前 release-facing 基線

目前 repository 與 CI reader 對齊：
- [v1.2.0](v1.2.0.md)
- [v1.2.0 GitHub Release 草稿](v1.2.0-github-release.md)
- [v1.2.0 發布檢查清單](v1.2.0-publish-checklist.md)
- [Alpha 信心檢查清單](alpha-checklist.md)

說明：
- `v1.2.0` 是目前文件與 CI release reader 使用的版本。
- 文件、bundle 與 checklist 就緒不等於 GitHub Release 或 tag 已發布；遠端發布狀態必須另外驗證。
- `main` 後續的 unreleased 變更仍應以 `CHANGELOG.md` 的 Unreleased 區段理解，不應倒推成 `v1.2.0` 已發版能力。

## 歷史版本

- [v1.1.0](v1.1.0.md)
- [v1.1.0 GitHub Release 草稿](v1.1.0-github-release.md)
- [v1.1.0 發布檢查清單](v1.1.0-publish-checklist.md)
- [v1.0.0-alpha](v1.0.0-alpha.md)
- [v1.0.0-alpha GitHub Release 草稿](v1.0.0-alpha-github-release.md)
- [v1.0.0-alpha 發布檢查清單](v1.0.0-alpha-publish-checklist.md)

## 本地生成的 Release Package

本 repo 也會把 release package 與 publication reader 的輸出落到本地文件路徑：
- [Generated Release Root](generated/README.md)

常用命令：
```bash
python governance_tools/release_package_snapshot.py --version v1.2.0 --publish-docs-release --format human
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
python governance_tools/release_surface_overview.py --version v1.2.0 --format human
```

## 相關入口

- [Status Index](../status/README.md)
- [Runtime Governance 現況](../status/runtime-governance-status.md)
- [Trust Signal Dashboard](../status/trust-signal-dashboard.md)
- [README](../../README.md)
