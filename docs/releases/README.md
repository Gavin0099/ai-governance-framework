# Release Index

This directory is the stable entry point for release-facing artifacts in `ai-governance-framework`.

## Current Release

- [v1.1.0](v1.1.0.md)
- [GitHub Release Draft](v1.1.0-github-release.md)
- [Publish Checklist](v1.1.0-publish-checklist.md)
- [Alpha Checklist](alpha-checklist.md)

## Previous Releases

- [v1.0.0-alpha](v1.0.0-alpha.md)
- [v1.0.0-alpha GitHub Release Draft](v1.0.0-alpha-github-release.md)
- [v1.0.0-alpha Publish Checklist](v1.0.0-alpha-publish-checklist.md)

## Generated Release Packages

- [Generated Release Root](generated/README.md)

Use these commands when you want to regenerate and read the latest release package:

```bash
python governance_tools/release_package_snapshot.py --version v1.1.0 --publish-docs-release --format human
python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human
python governance_tools/release_surface_overview.py --version v1.1.0 --format human
```

## Related Status Surfaces

- [Status Index](../status/README.md)
- [Trust Signal Dashboard](../status/trust-signal-dashboard.md)
