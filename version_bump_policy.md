# Version Bump Policy

This policy defines when `ai-governance-framework` should bump release version.

## Core Rule

Not every change requires a version bump.

Use semantic versioning intent:

- `major`: breaking compatibility change
- `minor`: new compatible capability
- `patch`: compatible fix or behavior refinement
- `none`: documentation/memory/report-only changes

## Bump Matrix

1. `none` (no bump)
- only `docs/`, `memory/`, `artifacts/`, `archive/`, `*.md` narrative updates
- no runtime/tooling behavior change

2. `patch`
- bug fix in existing governance/runtime/tooling behavior
- output additions that do not break existing consumers
- test updates accompanying compatible fixes

3. `minor`
- new governance capability, new check, new command, new rule pack behavior
- compatible new output surface (new optional section/field)

4. `major`
- breaking schema/contract/runtime behavior change
- removal or rename of existing required fields/surfaces
- stricter compatibility floor that can reject previously valid consumers
- explicit bump of runtime required versions

## Authority And Source Of Truth

- Current release is read from `README.md` / `CHANGELOG.md`.
- Consumer compatibility lock is tracked via `governance/framework.lock.json`.
- Runtime compatibility floor is tracked in `governance/runtime/required_versions.yaml`.

## Operational Guidance For Agents

1. Run:
```bash
python governance_tools/version_bump_guard.py --format human
```

2. Follow recommendation:
- `recommended_bump=none` -> do not bump
- `recommended_bump=patch|minor|major` -> bump accordingly

3. If recommendation is `major`, require explicit human confirmation before release tagging.

## Notes

- This policy is for versioning discipline, not release authority.
- Release claim authority remains under governance authority contracts.
