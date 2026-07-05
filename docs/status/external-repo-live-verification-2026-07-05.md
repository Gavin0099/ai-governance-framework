# External Repo Live Verification — 2026-07-05

Status: VERIFICATION REPORT / READ-ONLY (revised same day — see Correction)
Framework HEAD: 750540d (initial pass); evidence rerun at cd08b59
Surfaces used: `runtime_hooks/smoke_test.py --event-type session_start`
(direct smoke) and `runtime_hooks/dispatcher.py` shared session_start replay,
per the runtime-smoke skill. No external repo was modified.

## Scope and Reachability

Reachable (D: drive): Kernel-Driver-Contract, USB-Hub-Firmware-Architecture-
Contract, IC-Verification-Contract, Enumd, Hearth, ZoneTruth.

NOT reachable this session: the E: drive is not mounted, so CFU, hid-spec,
hub-spec, verilog-domain-contract, and all company repos in
`governance_repo_matrix.ps1` could not be verified. No claim is made about
them.

## Results

| Repo | version_manifest | Direct smoke (session_start) | Dispatcher replay | Failure class |
| :--- | :--- | :--- | :--- | :--- |
| Kernel-Driver-Contract | missing | ok=False, `controlled_refusal`, `version_compatibility_unsupported` | ok=False, same | onboarding drift |
| USB-Hub-Firmware-Architecture-Contract | missing | same | same | onboarding drift |
| IC-Verification-Contract | missing | same | same | onboarding drift |
| Enumd | present | ok=False, `PLAN.md freshness is CRITICAL` (contract/validators resolve) | same | repo-local stale PLAN |
| Hearth | present | same | same | repo-local stale PLAN + embedded framework checkout noise |
| ZoneTruth | present | same | same | repo-local stale PLAN |

All 12 runs (6 repos x 2 surfaces) exited 1. Full commands, exit codes, and
raw stdout are preserved as durable receipts — see Evidence Artifacts below.

## Correction (same-day revision)

The initial pass of this report claimed Enumd / Hearth / ZoneTruth "PASS" on
the direct smoke surface, based on reading only the tail of the human-format
output (resolved skills/validators). The auditable rerun shows their direct
smoke results are also `ok=False` with `PLAN.md freshness is CRITICAL`: both
surfaces agree, and the earlier "Surface Semantics Note" claiming the direct
smoke path does not enforce PLAN freshness was a reading error, now retracted.
This correction is itself evidence for the review requirement that raw
outputs be preserved: the summary-only first pass misread a surface.

## Failure Classes

### 1. Onboarding drift: missing `.governance/version_manifest.yaml` (3 repos)

The three hardware contract repos predate the version-compatibility gate.
`session_start` fail-closes with `version_compatibility_unsupported`
(`version_manifest_load_error:not_found:...`). This is the gate working as
designed against un-migrated consumers, not a framework regression. Remedy is
an onboarding refresh per repo (F-7 / adopt path), which is a separate
decision because it modifies external repos.

Smallest reproducer:

```bash
python runtime_hooks/smoke_test.py --event-type session_start \
  --contract D:/Kernel-Driver-Contract/contract.yaml --format json
```

### 2. Stale PLAN (3 repos)

Enumd / Hearth / ZoneTruth pass contract resolution, validator loading, and
version compatibility, but the dispatcher replay path enforces PLAN freshness
and all three PLans date from the June pause window (Enumd PLAN last touched
2026-06-19, last commit 2026-06-20). This is a true reflection of paused
repos, not a tooling failure. It clears naturally when work resumes and PLAN
is updated.

### 3. Embedded framework checkout noise (Enumd and Hearth)

Language-pack signals for both Enumd and Hearth reference
`ai-governance-framework/.latest-main/...` and `ai-governance-framework/tests/...`
paths inside their worktrees. A framework checkout embedded in a consumer repo
is the expected submodule-style consumer layout, and `.latest-main` is a
tracked directory of the framework itself, so it travels with any checkout.
The finding is therefore signal pollution, not necessarily a stray copy: the
language-pack scanner suggests packs based on the embedded framework's own
fixture files. Whether these checkouts are the intended consumer layout needs
owner confirmation; if they are, the scanner should learn to exclude embedded
framework paths.

## Evidence Artifacts (command matrix)

Each of the 12 runs was executed through
`governance_tools.test_evidence_receipt_writer`, producing a durable
`test_evidence_receipt.v0.1` (full command, exit code, timestamps) plus raw
stdout, committed under:

`artifacts/evidence/external-verification-2026-07-05/<Repo>-<surface>.json` (receipt)
`artifacts/evidence/external-verification-2026-07-05/<Repo>-<surface>.txt` (raw output)

Surfaces: `smoke` = `runtime_hooks/smoke_test.py --event-type session_start
--contract D:/<Repo>/contract.yaml --format json`; `dispatcher` =
`runtime_hooks/dispatcher.py --file
runtime_hooks/examples/shared/session_start.shared.json --contract
D:/<Repo>/contract.yaml --format json`. All 12 exit codes were 1. Replaying
any row is one command taken verbatim from its receipt's `command` field.

## Cannot Claim

- E:-drive repos (CFU, hid-spec, hub-spec, verilog-domain-contract, company
  repos) verified — unreachable this session;
- the three contract repos are governance-ready — they fail-closed at
  session_start;
- the stale PLans are an error — they reflect the pause truthfully;
- any external repo state was fixed — this was read-only verification.

## Suggested Next Decisions (owner: repo owner)

1. Onboarding refresh for the three hardware contract repos (adds
   `.governance/version_manifest.yaml` via the governed update path).
2. Hearth nested-framework-copy cleanup.
3. Re-run this verification with the E: drive mounted to cover CFU and the
   company repos.
