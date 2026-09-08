# Gate 3 Historical Branch / Main Conflict-Resolution Packet

Date: 2026-08-24

Status: `REVIEW_PACKET_ONLY`

## Decision summary

The historical Gate 3 branch cannot be updated from current `origin/main` by
blindly choosing either side. A three-way merge preview reports four conflict
paths. This packet fixes the intended resolution policy for each path, but does
not create resolved bytes, a merge commit, a rebase, or a push.

| Conflict path | Decision | Required result |
|---|---|---|
| `PLAN.md` | `SEMANTIC_MERGE` | Keep current-main MRCSP and solo-owner merge-authority progress; keep the historical branch's later Gate 3 blocker closure and materialized-root state. Do not accept either file wholesale. |
| `docs/status/gate3-historical-task-source-reproduction-preflight-2026-08-21.md` | `MAIN_EXACT_BLOB` | Use current main blob `f81b51f992df3756eef7b9c6791dd4b9bd5897f2`. |
| `memory/04_review_log.md` | `APPEND_ONLY_UNION` | Preserve every existing branch record and insert main-only canonical record `ac60d148...` before the two 2026-08-24 branch records. |
| `memory/2026-08-20.md` | `IDENTITY_UNION` | Preserve all 12 distinct record identities: the branch's ten records in their existing order, followed by main's two later session records in their existing order. |

## Frozen integration inputs

- Historical branch head: `f7153e8418e1e126e8ca4652bebde2219f97fefa`
- Current main: `f788e2b0e0a825e19f267fee42eb8519f329fd64`
- Merge base: `f802dba4ee4a28239f6d6862309e458b0eaf3550`
- Divergence at packet creation: 86 main-only commits and 15 branch-only commits.
- Patch-equivalence audit: four branch commits already have patch-equivalent
  changes in main (`01b5bd25`, `bb0a9513`, `d0defb48`, `08990fd3`); eleven
  branch commits remain branch-only.
- Preview command: `git merge-tree <merge-base> <branch-head> origin/main`.
- Preview result: exactly four conflict sections: two `changed in both` and
  two `added in both`, corresponding to the four paths above.

The integration must use a merge commit. Squash or rebase would discard the
reviewed branch ancestry and can strand commit bindings recorded by the memory
checkpoints.

## Path decision 1 — `PLAN.md`

### Exact inputs

- Merge-base blob: `dfe3ad28491cf7b7278ee8b6fde45fb3f5e21c65`
- Branch blob: `e473d9ecf7b0ab95a1291f23b51720a2661a5356`
- Main blob: `7acf03c719961046cd07571a90df9e782a10ef9a`

### Decision

`SEMANTIC_MERGE`.

Current main adds valid 2026-08-24 planning state for the MRCSP M0/M1a work and
the solo-owner merge-authority correction. The historical branch contains the
later Gate 3 state established by its branch-only commits: BLOCKED-3 is closed,
measured layouts exist, the materialized-root transport decision is accepted,
and M3-b-2 remains unimplemented rather than blocked on a missing design.

The resolved file must therefore:

1. retain main's MRCSP M0/M1a and solo-owner merge-authority sections;
2. retain the branch's Gate 3 statements that BLOCKED-3 is closed and the
   materialized-root transport design is resolved;
3. reject main's stale Gate 3 wording that these branch-only results are not
   merged, BLOCKED-3 remains open, or the root transport is unresolved;
4. set the planning freshness date to `2026-08-24`; and
5. avoid introducing any new Gate 1, A/B/C/D, attempt-05, effectiveness, or
   promotion claim.

This decision is not evidence that the branch-only Gate 3 work has already been
accepted into main. It only prevents a merge resolution from rewriting its
historical state backwards.

## Path decision 2 — reproduction preflight

Path: `docs/status/gate3-historical-task-source-reproduction-preflight-2026-08-21.md`

### Exact inputs

- Merge base: path absent
- Branch blob: `1d5d560ad9a98299ec6c348e6f9eadac3b97f219` (15,303 bytes)
- Main blob: `f81b51f992df3756eef7b9c6791dd4b9bd5897f2` (15,764 bytes)

### Decision

`MAIN_EXACT_BLOB`.

The main version differs only by the reviewed early-stop evidence amendment:
it permits either two role receipts or one executed-role receipt plus a bound
terminal attempt record explaining why the other role did not run. It also
defines the required bindings for that terminal record. This is a strict,
documented successor to the branch blob; no branch-only sentence is lost by
selecting it.

The future merge resolution should take the main blob byte-for-byte. It must
not reconstruct, paraphrase, or combine the two variants manually.

## Path decision 3 — `memory/04_review_log.md`

### Exact inputs

- Merge-base blob: `1053d57b74de39af696e7fd15b53aa1bad53c7fc`
- Branch blob: `50bb159d1983b219aaa1f807f1b8d6d7de0e3f25`
- Main blob: `9c68a2b65ded9a8b74cf97a786af356e05a916b5`

### Marker census

- Branch canonical markers: 5
- Main canonical markers: 4
- Shared markers: `921da152...`, `70f02f4a...`, `8f7d0de3...`
- Branch-only markers: `12bbe5f6...`, `1e46e921...`
- Main-only marker: `ac60d148...`

### Decision

`APPEND_ONLY_UNION`.

The resolved log must preserve the complete branch log, preserve the main-only
`ac60d148...` closure record, and contain each full marker line exactly once.
Chronological placement is fixed:

1. the three shared 2026-08-23 records;
2. main-only `ac60d148...` (`2026-08-23-10`);
3. branch-only `12bbe5f6...` (`2026-08-24-16`);
4. branch-only `1e46e921...` (`2026-08-24-17`).

No historical record may be rewritten to make an earlier pending state look as
if it was known at write time. Deduplication is by complete canonical marker
identity, not by substring or prose similarity. The merged file must pass the
canonical memory authority guard.

## Path decision 4 — `memory/2026-08-20.md`

### Exact inputs

- Merge base: path absent
- Branch blob: `80ede0f0c3850bb0f49750d5fb9fca6a491cd578` (12,774 bytes)
- Main blob: `8b0eef87013750cf413560d63a44ea813df3faf7` (1,846 bytes)

### Identity census

The two sides contain no duplicate `record_identity` values.

Branch records, existing order:

1. `d5e13508...`
2. `ff8ce153...`
3. `f96fbc31...`
4. `9dea60a1...`
5. `d64b293b...`
6. `94e08ddc...`
7. `4709f167...`
8. `c1c99162...`
9. `ad6cfaf1...`
10. `8422293c...`

Main records, existing order:

11. `c150d267...`
12. `bffc6ef7...`

### Decision

`IDENTITY_UNION`.

Preserve the branch's ten complete YAML records in their existing order, then
append main's two complete later-session records in their existing order. Do
not replace the branch file with main, replace main with the branch, rewrite a
record, or infer semantic duplication from similar prose. The resolved file
must contain exactly 12 unique full record identities and pass the canonical
memory workflow and authority guard.

## Required future resolution validation

A separately authorized merge-resolution slice must, before commit:

1. prove the merge parent pair is exactly `f7153e84...` and the then-current
   reviewed main commit (or produce a new packet if main moved);
2. confirm the conflict set has not expanded beyond the four paths;
3. verify the preflight path equals blob `f81b51f9...` exactly;
4. verify the review log contains all six unique canonical marker identities
   exactly once;
5. verify the daily memory file contains exactly the 12 identities listed here;
6. run `python -m governance_tools.memory_workflow --check --repo . --run-guard --fail-on-blocker`;
7. run the PLAN/memory scoped checks and a full staged `git diff --check`. A
   full-check finding may be classified as inherited from the main parent only
   when every reported path is introduced solely by that parent, each staged
   blob is byte-identical to the corresponding `origin/main` blob, and a
   separate scoped `git diff --cached --check` over the five resolution paths
   (`PLAN.md`, the preflight, both memory files, and this packet) passes. Any
   finding outside that conjunction remains fail-closed. Then run the
   repository's canonical precommit boundary gate; and
8. stop for review before push.

If `origin/main` changes after this packet, the exact main binding and conflict
set are stale. Do not silently reuse these decisions against a different main
head; refresh the packet or explicitly review the delta first.

## Claim ceiling and non-actions

This packet establishes a reviewer-facing resolution policy for four observed
merge conflicts only. It does not:

- produce resolved merge bytes or prove that a future merge is conflict-free;
- merge, rebase, squash, commit, push, or alter the dirty primary worktree;
- accept the branch-only Gate 3 commits into main;
- remove the primary worktree's temporary untracked identity config;
- reconcile unrelated dirty files or M3-b-2A working-tree edits;
- authorize attempt-05, Gate 1 preregistration, A/B/C/D execution, Skill
  effectiveness, Gate 3 effectiveness, promotion evidence, or process-integrity
  claims.
