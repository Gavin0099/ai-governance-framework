# S2: product GDScript source suggestions

Owner authorized separate framework S1/S2 commits, pushes and Draft PRs.
This packet covers S2 implementation `4e2b05ad`, stacked on S1 Draft PR #209
at `798b85a6`. The implementation changes exactly two files.

## Behavior and boundary

- Product `.gd` files participate in the existing count/share confidence model.
- `project.godot` alone, Godot C# projects and test-only `.gd` are not GDScript proof.
- Documents, fixtures, dot-metadata and embedded frameworks remain excluded.
- Mixed Python/GDScript and sparse GDScript cases have fixed expected outcomes.
- Suggestions remain advisory. Registry activation remains explicit-only.
- No confidence-threshold, repo-type classifier, Runtime, gate-policy or consumer change.

## Evidence

- `s2-committed-tests.json`, `.xml` and `.txt`: 66 focused cases against S2 HEAD.
- `s2-precommit.log`: shared multi-platform smoke and 207 Runtime cases.
- The full S1 scope is reviewed separately in PR #209.

Current evidence is stored under the required memory root; formal memory
evidence-root provenance qualification remains unclaimed. Earlier local
combined-candidate observations are historical and excluded from S2 delivery.

## Next gate

Review each exact Draft head and its checks. S2 must remain stacked on S1;
neither Draft authorizes merge, release, consumer pin adoption, native gameplay
acceptance or complete governance adoption.
