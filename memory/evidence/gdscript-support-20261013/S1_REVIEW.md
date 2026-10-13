# S1: explicit GDScript support

Owner authorized separate framework S1/S2 commits, pushes and Draft PRs.
This packet covers S1 implementation commit `6cd672cb` only.

## Problem and behavior

DiceMercenaries cannot truthfully declare its GDScript sources under the old
canonical language enum. S1 accepts `LANG = GDScript`, provides one non-empty
language pack and supports explicit `RULES = common,gdscript` loading.
The registry entry is explicit-only; S1 does not detect product `.gd` files.

## Frozen boundary

- Implementation: 19 enum/validator/registry/pack/projection/test files.
- Tests after the implementation commit: 236 cases, zero failures.
- Standard precommit: shared multi-platform smoke and 207 Runtime tests passed.
- Nine generated checkpoint projections agree with the canonical digest.
- No core Runtime, gate policy, evidence threshold, schema or consumer pin change.
- No merge, release, native game validation, owner classification or full adoption claim.

## Current evidence

- `s1-committed-tests.json`: wrapper receipt linked to implementation HEAD.
- `s1-committed-tests.xml` and `.txt`: focused result and raw output.
- `s1-committed-projections.json`: nine projection checks.
- `s1-precommit.log`: standard gate result.

Earlier combined-candidate observations remain historical in the daily record
and their original snapshots are retained locally. Those S2/combined snapshots
are excluded from this S1 PR and are not current S1 validation evidence. Their
original unbound state is preserved. S2 source changes are reserved for a
stacked PR.

Evidence files remain under the required repository memory root. That root is
not declared as an admissible evidence root in the framework contract, so formal
memory test-evidence provenance qualification is not claimed. The authority guard
reports existing/historical warnings separately from active blockers.

## Next gate

Review the exact Draft head and CI. S2 is a separate stacked delivery;
consumer S3/S4 and governed pin adoption remain pending framework review.
