# External Repo Live Verification — 2026-07-05

Status: VERIFICATION REPORT / READ-ONLY
Framework HEAD: 750540d
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
| Kernel-Driver-Contract | missing | `blocked` / `controlled_refusal`, `version_compatibility_unsupported` | ok=False | onboarding drift |
| USB-Hub-Firmware-Architecture-Contract | missing | same | ok=False | onboarding drift |
| IC-Verification-Contract | missing | same | ok=False | onboarding drift |
| Enumd | present | PASS (skills/validators/evidence resolved) | `PLAN.md freshness is CRITICAL` | repo-local stale PLAN |
| Hearth | present | PASS | `PLAN.md freshness is CRITICAL` | repo-local stale PLAN + hygiene finding |
| ZoneTruth | present | PASS | `PLAN.md freshness is CRITICAL` | repo-local stale PLAN |

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

### 3. Hygiene finding: nested framework copy inside Hearth

Dispatcher language-pack signals for Hearth reference
`ai-governance-framework/.latest-main/runtime_hooks/...` paths inside the
Hearth worktree — a nested copy of this framework (including its
`.latest-main` snapshot) is present there and is polluting repo signals. Same
family as the nested-copy findings in the framework repo's own hygiene review.
Cleanup belongs to the Hearth repo.

## Surface Semantics Note

Direct smoke and dispatcher replay legitimately disagree: the direct smoke
path for these contracts does not enforce PLAN freshness, the dispatcher
replay does. Treat them as different surfaces (per the runtime-smoke skill);
neither result invalidates the other.

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
