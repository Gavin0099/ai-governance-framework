# Generated Release Packages

這個目錄存放由工具產生的 repo-local release package snapshot。  
它不是正式對外發布頁，而是 generated entrypoint，主要供：
- release package 檢查
- publication reader
- 本地驗證與對照

目前常見輸出包括：
- `latest.md`
- `latest.json`
- `PUBLICATION_MANIFEST.json`
- `PUBLICATION_INDEX.md`
- `<version>/README.md`
- `<version>/MANIFEST.json`

若要在本地生成 release package：

```bash
python governance_tools/release_package_snapshot.py --version v1.0.0-alpha --publish-docs-release --format human
```

若要讀取 generated release root：

```bash
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
```
