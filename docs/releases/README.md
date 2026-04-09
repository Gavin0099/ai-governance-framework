# 發版索引

更新日期：2026-04-09

本目錄收錄 `ai-governance-framework` 的正式發版文件、GitHub Release 草稿、發版檢查清單，以及本地產生的 release package 入口。

## 目前正式對外版本

目前最後一個正式對外版本為：
- [v1.1.0](v1.1.0.md)
- [v1.1.0 GitHub Release 草稿](v1.1.0-github-release.md)
- [v1.1.0 發布檢查清單](v1.1.0-publish-checklist.md)
- [Alpha 信心檢查清單](alpha-checklist.md)

說明：
- `v1.1.0` 是目前正式 release-facing 版本。
- `main` 分支後續已累積較新的 runtime、closeout、advisory、adoption hardening 變更；那些變更應以 `README.md`、`docs/status/` 與對應設計文件理解，不應倒推成已正式發版能力。

## 歷史版本

- [v1.0.0-alpha](v1.0.0-alpha.md)
- [v1.0.0-alpha GitHub Release 草稿](v1.0.0-alpha-github-release.md)
- [v1.0.0-alpha 發布檢查清單](v1.0.0-alpha-publish-checklist.md)

## 本地生成的 Release Package

本 repo 也會把 release package 與 publication reader 的輸出落到本地文件路徑：
- [Generated Release Root](generated/README.md)

常用命令：
```bash
python governance_tools/release_package_snapshot.py --version v1.1.0 --publish-docs-release --format human
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
python governance_tools/release_surface_overview.py --version v1.1.0 --format human
```

## 相關入口

- [Status Index](../status/README.md)
- [Runtime Governance 現況](../status/runtime-governance-status.md)
- [Trust Signal Dashboard](../status/trust-signal-dashboard.md)
- [README](../../README.md)
