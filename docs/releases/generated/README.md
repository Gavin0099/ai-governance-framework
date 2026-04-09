# 產生的 Release Packages

????曄撌亙?Ｙ???repo-local release package snapshot?? 
摰??舀迤撘?憭撣?嚗 generated entrypoint嚗蜓閬?嚗?- release package 瑼Ｘ
- publication reader
- ?砍撽?????
?桀?撣貉?頛詨?嚗?- `latest.md`
- `latest.json`
- `PUBLICATION_MANIFEST.json`
- `PUBLICATION_INDEX.md`
- `<version>/README.md`
- `<version>/MANIFEST.json`

?亥??冽?啁???release package嚗?
```bash
python governance_tools/release_package_snapshot.py --version v1.0.0-alpha --publish-docs-release --format human
```

?亥?霈??generated release root嚗?
```bash
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
```
