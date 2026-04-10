# 產生的 Release Packages

這個目錄放的是由工具產生的 repo-local release package snapshot。  
它的角色是 generated entrypoint，不是手寫 release 文檔。

目前主要包含：
- release package 驗證輸出
- publication reader 入口
- 各版本對應的 generated bundle

常見檔案包括：
- `latest.md`
- `latest.json`
- `PUBLICATION_MANIFEST.json`
- `PUBLICATION_INDEX.md`
- `<version>/README.md`
- `<version>/MANIFEST.json`

若要產生某個 release package：

```bash
python governance_tools/release_package_snapshot.py --version v1.0.0-alpha --publish-docs-release --format human
```

若要讀取整個 generated release root：

```bash
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
```
