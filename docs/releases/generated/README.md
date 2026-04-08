# Generated Release Packages

這個目錄是 generated release-package snapshot 的穩定 repo-local 落點。

當 release-package publishing 跑過後，最新的 generated entrypoint 會維持在這裡：

- `latest.md`
- `latest.json`
- `PUBLICATION_MANIFEST.json`
- `PUBLICATION_INDEX.md`
- `<version>/README.md`
- `<version>/MANIFEST.json`

可用以下命令生成或刷新這個路徑：

```bash
python governance_tools/release_package_snapshot.py --version v1.0.0-alpha --publish-docs-release --format human
```

可用以下命令讀取 generated release root：

```bash
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
```
