# Review delivery integration

This adapter connects Antigravity's native `PreToolUse` event to the three
review primitives delivered at `afdb60b3`. It adds no finding parser or review
predicate. `assess_blocking_findings()` remains the only decision implementation.

## Boundary

```
run_command proposes a supported direct gh pr merge
  -> read the live GraphQL snapshot in that command's Cwd/repository context
  -> read the explicitly configured existing assessment ledger
  -> assess_blocking_findings(snapshot, ledger.review_id, ledger)
  -> not PASS: native deny
  -> PASS: native ask (ordinary command authorization still applies)
```

`REVIEW_GATE=PASS` means only that the existing review predicates passed.
`MERGE_READY` stays `NOT_EVALUATED`. CI, authorization, base state, dirty state,
reviewer qualification, and atomic protection at the actual merge remain separate.
No code in this adapter executes a merge or writes GitHub/local delivery state.

The platform output is `decision` plus `reason`. `reason` contains JSON with
`REVIEW_GATE`, `MERGE_READY`, and the unchanged primitive results. In this JSON,
`UNKNOWN` means review qualification is unavailable, not zero findings.

## Local configuration

Create the following named hook in the consumer's `.agents/hooks.json`, merging
with any existing named hooks rather than replacing the file:

```json
{
  "review-delivery": {
    "enabled": true,
    "PreToolUse": [{
      "matcher": "run_command",
      "hooks": [{
        "type": "command",
        "command": "D:/ai-governance-framework/.venv/Scripts/python.exe -I D:/ai-governance-framework/governance_tools/review_delivery_hook.py --config D:/ruiyi-life-map/.agents/review-delivery.json",
        "timeout": 30
      }]
    }]
  }
}
```

The accompanying `.agents/review-delivery.json` contains two explicit paths:

```json
{
  "gh_executable": "C:/Program Files/GitHub CLI/gh.exe",
  "assessment_path": "D:/ruiyi-life-map/memory/review-delivery-assessment.json"
}
```

These are machine-specific example paths. The configured interpreter/framework
and ledger must exist at their declared locations. An absent ledger denies a
supported merge proposal; installation does not fabricate one or grant readiness.
The ledger format is the existing format in `SLICE3.md`. Select a review ID and
classify every acquired source explicitly; the adapter never chooses a reviewer
or repairs a stale assessment hash. Use the existing `review_evidence --print-query`
command to obtain the acquisition query when preparing the ledger.

The production read-only query uses GitHub CLI's `owner={owner}` and `name={repo}`
substitution in the proposed command's `Cwd`, so it follows that repository
context. This deliberately retains the existing GitHub CLI environment/config
trust boundary. An absolute executable path is required, but executable bytes,
PATH-resolved Git helpers, credentials, and Git/GitHub configuration are not
authenticated by this slice.

Framework imports come from the configured framework script's directory with
Python `-I`; they do not come from the consumer's working directory. A local
framework path does not upgrade the consumer's pinned framework version and
requires that local checkout to remain available. No global configuration or
skill-loading behavior is changed by this setup.

## Covered command forms

The only command form qualified for `PASS` uses the configured absolute executable path
itself (optionally quoted and optionally preceded by PowerShell `&`). It requires a
positive numeric PR number. Supported arguments are
`--merge`, `--squash`, `--rebase`, `-m`, `-s`, `-r`, `--delete-branch`, and
`--match-head-commit` followed by a full SHA. A recognized direct merge prefix
with other arguments is denied as unsupported.

Bare `gh` / `gh.exe` and a different direct `gh.exe` path are recognized as
merge-shaped but denied as `UNKNOWN`; the hook cannot prove that shell resolution would use
the configured executable. Use that exact configured absolute path for a supported merge.

Other commands return `ask` without reading the ledger or querying GitHub.
This is the platform's permission path, not `allow`. It can still ask the user
when a command lacks an existing grant. Wrappers, aliases, functions, scripts,
GitHub UI/API mutations, and shell programs that conceal a merge are not covered.
The `gh --repo OWNER/REPO pr merge` form is also not matched because global options
before `pr merge` are outside this parser; standard command permissions still apply.
This adapter is not a command firewall or repository-wide merge protection.

## Native qualification and replay

Use a separate temporary workspace and an inert command stub. Never propose a
real GitHub merge as a test. `native_hook_replay.py` is a test-only native handler:
it preserves the native event and real adapter/primitives, replacing only live
acquisition with a frozen fixture. The requested PR must match the chosen case.
It records the native event and handler response in a temporary JSONL file.

```text
python -I <framework>/tests/fixtures/review_evidence/native_hook_replay.py
  --case pr81_complete --gh <absolute-inert-stub> --record <temporary-output>
```

Other cases are `pr81_incomplete` and `pr80_complete`. Install this command only
in the temporary workspace's named `PreToolUse` hook. Start Antigravity CLI with
`--add-dir <temporary-workspace>`: process Cwd alone must not be assumed to mount
the workspace or load its hooks. Ask for one direct merge-shaped invocation using
the exact absolute inert stub path passed to `--gh` (quote it when needed).
Inspect the actual callback and platform decision, not merely
the model's summary or the CLI process exit code.

Expected results:

| Case | Review result | Native handoff |
| --- | --- | --- |
| PR81 incomplete acquisition | UNKNOWN / MERGE_READY=NO | deny |
| PR81 complete, old review HEAD | UNKNOWN / MATCH=NO / MERGE_READY=NO | deny |
| PR80 complete, matching ledger | PASS / MERGE_READY=NOT_EVALUATED | ask |

For the positive case, lack of command authorization in headless mode may still
deny execution. That is independent of the review result and must not be counted
as a review false-block. Do not disable permissions to make this test pass.
No native response may automatically authorize execution via `allow`.

Check non-target commands against the no-hook permission baseline as well.
An empty `{}` response is not a safe default: the qualified CLI denied it.
Native CLI qualification must not be reported as desktop/IDE qualification;
each active platform/version needs its own callback evidence. Configuration
presence alone does not prove that a running application has loaded the hook.

The PR80 frozen snapshot includes fields absent from the minimal live query.
Its existing assessment hash therefore cannot be reused for a new live capture.
A fresh capture needs an explicit content assessment bound to that exact JSON.

References: [Antigravity hook contract](https://www.antigravity.google/docs/hooks),
[GitHub CLI API substitution](https://cli.github.com/manual/gh_api).
