# AI Governance First Import SOP

Date: 2026-05-06

## Objective

Provide a repeatable process for first-time AI governance import into a consuming repo that has no complete governance baseline yet.

## Scope Boundary

- In scope: governance scaffold import, runtime/governance validation, report artifact.
- Out of scope: domain business logic changes (for example firmware/driver/protocol code).

## Execution Context (Mandatory)

Unless otherwise stated:

- `adopt_governance.py` commands are executed from `ai-governance-framework` repo root.
- validation commands are executed from consuming repo root after adoption.

If command context is ambiguous, stop and print current working directory before continuing.

## Minimum Viable Governance Baseline (MVGB)

First import is not considered complete unless all of the following are present and meaningful:

- `AGENTS.md` is repo-specific and not generic placeholder-only content.
- `.governance/version_manifest.yaml` exists and is syntactically valid.
- `governance/framework.lock.json` exists and records framework source/release/commit.

## Procedure

1. Clone and prepare
- clone framework and consuming repo in the same workspace
- confirm target repo root and Python interpreter

2. Preflight with dry-run
- run:
```powershell
python governance_tools/adopt_governance.py --target <repo> --dry-run
```
- review planned file actions before writing

3. Execute adoption
- run:
```powershell
python governance_tools/adopt_governance.py --target <repo>
```

4. Resolve common first-import gaps
- ensure these files exist and are valid:
  - `.governance/version_manifest.yaml`
  - `governance/framework.lock.json`
  - `governance/gate_policy.yaml`
- ensure `AGENTS.md` is not left as generic placeholder-only content
- treat these as MVGB requirements, not optional improvements

<a id="submodule-framework-lock"></a>
### 4.1 Repair the submodule consumer framework lock

For a consumer that imports the framework as a Git submodule, F-7 can report
`full_update_completed` with no consumer `governance/framework.lock.json`.
That status describes the update stages. Formal closeout preparation separately
requires this lock to be a tracked, clean regular file, with `adopted_commit`
equal to the framework gitlink in the consumer's index. F-7's missing-lock
warning is guidance only; it does not write the lock or change update success.

Run the following from the **consumer root**. Use this consumer's registration
and pinned metadata; do not copy another repo's lock or the framework's own
self-assessment lock.

1. Find the registered path and source URL in `.gitmodules`.

```powershell
git config --file .gitmodules --get-regexp '^submodule\..*\.path$'
$submoduleName = '<submodule-name-from-.gitmodules>'
$submodulePath = git config --file .gitmodules --get "submodule.$submoduleName.path"
$sourceUrl = git config --file .gitmodules --get "submodule.$submoduleName.url"
```

Choose the entry for the framework, including a custom `<submodule-path>`.
`<submodule-name-from-.gitmodules>` is the section name, which can differ from
the path. Both lookups must succeed and return nonempty values. Keep the source
URL from this registration, including a relative URL if that is what it records.

2. Read the consumer's **index gitlink**, then read version metadata at that
   exact commit.

```powershell
git ls-files --stage -- "$submodulePath"
$gitlink = git rev-parse --verify ":$submodulePath"
git -C "$submodulePath" show "${gitlink}:README.md"
git -C "$submodulePath" show "${gitlink}:CHANGELOG.md"
```

The index entry must be exactly `160000 <gitlink> 0<TAB><submodule-path>`.
Missing or unmerged entries must be resolved first. Do not substitute
`git -C <submodule-path> rev-parse HEAD` for the index gitlink. Use the release
at `$gitlink`, following `current_framework_release`'s order: README list entry
(``- version: `<version>` ``), then README version badge, then the first CHANGELOG
release heading. A missing CHANGELOG is harmless when README supplies the
version; if no version is identifiable, resolve that before filling the lock.
Record the version without a leading `v`, as `current_framework_release`
returns it (a CHANGELOG heading `## v1.3.0` is recorded as `1.3.0`). Once the
checkout below is clean and its HEAD equals `$gitlink`, the framework's own
resolver prints that value:

```powershell
python -B -X utf8 -c "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from governance_tools.framework_versioning import current_framework_release; print(current_framework_release(Path(sys.argv[1])))" (Resolve-Path -LiteralPath "$submodulePath").Path
```
If the object is unavailable locally, obtain that pinned object from the
consumer's configured source before reading its metadata.

Inspect the checkout independently:

```powershell
git -C "$submodulePath" rev-parse HEAD
git -C "$submodulePath" status --porcelain=v1 --untracked-files=all
git diff --cached --name-only HEAD -- .gitmodules "$submodulePath"
```

Preparation also requires checkout HEAD to equal the index gitlink, a clean
framework checkout, and a committed gitlink and `.gitmodules`. If HEAD differs,
first preserve any local work. For a clean checkout intended to follow the
index pin, `git submodule update --init -- "$submodulePath"` aligns it. If the
owner intends to adopt a different revision, stage that approved gitlink,
re-read `$gitlink` and its version, and include the pin in the adoption commit.
Never conceal the mismatch by recording a different SHA in the lock.

3. Create the consumer's `governance/framework.lock.json` as a regular JSON
   object, replacing every placeholder with the values above.

```powershell
New-Item -ItemType Directory -Force -Path governance | Out-Null
```

Save the following as UTF-8 JSON at `governance/framework.lock.json`:

```json
{
  "framework_repo": "<source-url-from-this-consumers-.gitmodules>",
  "adopted_release": "<framework-version-at-index-gitlink>",
  "adopted_commit": "<full-index-gitlink>"
}
```

| Field | Value source and purpose |
| --- | --- |
| `framework_repo` | `$sourceUrl` from this consumer's `.gitmodules`; source metadata for framework version reporting. |
| `adopted_release` | Release read at `$gitlink`; release metadata for framework version reporting. |
| `adopted_commit` | Full `$gitlink` from the consumer index; the equality required by closeout preparation. |

`framework_interface_version` and `framework_compatible` are optional to this
preparation check. If the consumer declares them, retain its applicable
contract values, or inspect `git -C "$submodulePath" show "${gitlink}:governance/framework.lock.json"` for the pinned framework's declared
interface/range; do not invent a range. Do not copy `_self_reference_note` or
`_lock_file` into the consumer lock. The former describes framework
self-assessment; the latter is added in memory by the lock reader.

4. Review and commit the manual repair under the owner's commit authorization.
   Ensure no unrelated changes are staged before committing.

```powershell
git add -- governance/framework.lock.json
# Also stage .gitmodules and the submodule path if this approved adoption changed them.
git diff --cached -- .gitmodules governance/framework.lock.json "$submodulePath"
git commit -m "Record adopted framework lock"
git ls-files --stage -- governance/framework.lock.json
git status --porcelain=v1 -- .gitmodules governance/framework.lock.json "$submodulePath"
```

The lock's index entry must have mode `100644` and stage `0`; the status command
must produce no output. Merely adding it to the index leaves an uncommitted
control file. A committed but subsequently edited file is also rejected.

5. Check the existing preparation validator from the registered framework
   checkout. This invokes `validate_framework_binding` without preparing a
   candidate or executing closeout. `-B` avoids creating bytecode in the
   framework checkout. The validator refuses to run while the shell carries an
   inherited `GIT_*` variable it does not tolerate, and names them in
   `Git environment overrides unsupported: <names>`. Editor-integrated
   terminals often set some of them (for example `GIT_ASKPASS`). Run the check
   in a shell where the named variables are unset; in PowerShell, for the
   current session only: `Remove-Item Env:<NAME>` for each named variable.

```powershell
$consumerRoot = (git rev-parse --show-toplevel).Trim()
$frameworkRoot = (Resolve-Path -LiteralPath "$submodulePath").Path
python -B -X utf8 -c "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[2]); from governance_tools.prepare_closeout_candidate import validate_framework_binding; validate_framework_binding(Path(sys.argv[1]), Path(sys.argv[2])); print('framework binding validated; closeout not executed')" "$consumerRoot" "$frameworkRoot"
```

Success is exit code `0` and `framework binding validated; closeout not executed`.
This validates only the framework binding. For actual candidate preparation,
use the existing session ID and truthful candidate-input JSON with
`task_intent`, `work_summary`, `tools_used`, `artifacts_referenced`, and
`open_risks`:

```powershell
python -B -X utf8 "$submodulePath/governance_tools/prepare_closeout_candidate.py" --consumer-root "$consumerRoot" --framework-root "$frameworkRoot" --session-id "<existing-session-id>" --input "<candidate-input.json>"
```

Preparation succeeds with exit code `0`, JSON `status: PREPARED` and
`closeout_executed: false`. It requires an existing, unconsumed session binding
and writes a candidate plus shared preparation state; run it only when
preparing that session. It does not execute formal closeout.

Known binding rejection messages from the existing validator include:

- `tracked regular control file required: governance/framework.lock.json`
  for a missing/untracked lock or wrong index mode;
- `uncommitted control file: governance/framework.lock.json` for a staged or
  modified lock;
- `framework lock adopted_commit differs from index gitlink` for a wrong pin;
- `unmerged or missing index gitlink`, `uncommitted gitlink`,
  `checkout HEAD differs from index gitlink`, or `dirty framework checkout`
  for unresolved registration/pin/checkout state;
- `Git environment overrides unsupported: <names>` when the shell carries
  inherited `GIT_*` variables (see step 5); this is checked before the lock.

The binding-only command raises the existing error and exits nonzero. The
preparation CLI returns exit code `1` with JSON `status: REJECTED` and the
message in `error`. An existing lock alone never proves formal-closeout
eligibility; all existing preparation and handoff validations still apply.

5. Validate runtime/governance path
- run:
```powershell
python quickstart_smoke.py
python runtime_hooks/core/session_start.py --project-root . --plan-path PLAN.md --task "governance import validation" --rules common --risk low --oversight review-required --memory-mode candidate --format json
python runtime_hooks/core/pre_task_check.py --project-root . --task-text "governance import validation" --rules common --risk low --oversight review-required --memory-mode candidate --format json
python -m governance_tools.external_repo_readiness --format json
python -m governance_tools.governance_version_check --project-root . --format json
```

6. Optional but recommended
- install git hooks (`pre-commit`, `pre-push`)
- run onboarding report:
```powershell
python -m governance_tools.external_repo_onboarding_report --format json
```

6.1 One-command validation runner (recommended)
- run:
```powershell
python governance_tools/run_first_import_validation.py --repo-root .
```
- output file (default):
  - `AI_Governance_First_Import_Validation_<YYYYMMDD>.md`

7. Produce evidence report
- write one markdown report in consuming repo root, for example:
  - `AI_Governance_Import_Test_Report_<YYYYMMDD>.md`
- include:
  - imported framework version and commit
  - files added/updated for governance
  - command list + pass/fail summary
  - blocking vs non-blocking warnings

## Success Criteria

- `external_repo_readiness.ready = true`
- quickstart smoke passes
- session_start and pre_task_check pass without controlled refusal
- governance version check is compatible
- evidence report exists and includes exact command outputs or explicit artifact paths
- imported framework commit is explicitly recorded in the report

## Known Non-Blocking Warnings

- framework-side `expansion_boundary` warning
- hooks not installed (readiness may still be true)

## Fail-Fast Indicators

- `version_compatibility_unsupported`
- controlled refusal from `session_start` due to missing version manifest
- missing framework lock causing framework version state to be unknown/outdated
- `AGENTS.md` remains generic placeholder-only after adoption
