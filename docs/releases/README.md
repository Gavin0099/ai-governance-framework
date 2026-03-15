# Release Index

This directory is the stable entry point for release-facing artifacts in `ai-governance-framework`.

## Current Release

- [v1.0.0-alpha](v1.0.0-alpha.md)
- [GitHub Release Draft](v1.0.0-alpha-github-release.md)
- [Publish Checklist](v1.0.0-alpha-publish-checklist.md)
- [Alpha Checklist](alpha-checklist.md)

## Generated Release Packages

- [Generated Release Root](generated/README.md)

Use these commands when you want to regenerate and read the latest release package:

```bash
python governance_tools/release_package_snapshot.py --version v1.0.0-alpha --publish-docs-release --format human
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
```

## Related Status Surfaces

- [Status Index](../status/README.md)
- [Trust Signal Dashboard](../status/trust-signal-dashboard.md)
