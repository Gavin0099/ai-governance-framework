# Gate 3 C1 — Gate 0 Admission Checkpoint

Status: **`ADMITTED_AT_GATE0`**

Decision date: 2026-08-21

This checkpoint admits C1 only as a credible, reconstructable historical
product-bug candidate under Gate 0 of
[`evidence-backed-engineering-skill-program-2026-07-24.md`](../governance/evidence-backed-engineering-skill-program-2026-07-24.md).
It does not start Gate 1 or any experiment.

## Decision authority and scope

The owner explicitly authorized this bounded decision after independent review
approved the technical reproduction and found no technical blocker to Gate 0
admission. The authorized scope is:

- merge the immutable attempt-02 reproduction evidence;
- bind the historical baseline, fix, frozen oracle, and terminal evidence; and
- record C1 as `ADMITTED_AT_GATE0`.

The authority does not include Gate 1 preregistration, A/B execution, C2 or C3,
Route C activation, or any effectiveness or promotion claim.

## Authoritative bindings

| Surface | Binding |
|---|---|
| consumer repository | `https://github.com/Gavin0099/meiandraybook.git` |
| historical baseline | `15d5d51356b4808e5fb12782961a94d9985b2ae6` |
| historical fix | `a60756436095fb3b14aecbc9094dd88a8ab9ef16` |
| baseline relationship | the fix commit's direct parent is the historical baseline |
| fixed production path | `src/lib/integration/import-logic.ts` |
| frozen oracle | `702e0a78ec4d7e62abf57fd643bc068da559621428310fed2f22547b29ab9dad` / 8,411 bytes |
| attempt-02 manifest | `d0d5cc040a1561c10a1bf141d1a763b053588d5d1ae9a303108a328e5ddb5259` / 6,796 bytes |
| attempt-02 baseline receipt | `a70962406f6395c1e579c2df61564a6f011bef1402dd80d34a21f42357ba1375` / 3,756 bytes |
| attempt-02 fixed receipt | `adef9bdffafe9fb047355ec36b1f0e91d1eff22e87ef0a334c271b37f3975535` / 3,375 bytes |
| attempt-02 terminal | `8428a3d87c167ee363e0247ca47d6b1e695ea144e38073a5b5d00f1140edb959` / 2,760 bytes |
| pre-run framework commit | `ef7f221a88ba517a44de2562f15df1c131237e4e` |
| terminal framework commit | `c37e8accb9e008b72c755b30e033c1e3b1fa6452` |
| reproduction merge commit | `24d8981b33e66015c6428c1d72b902ba04f88cea` |

The attempt-02 files are retained under
`artifacts/experiments/prepush-bugfix-20260724/gate0-historical-reproduction/c1-strong-identity/attempt-c1-a607564-20260821-02/`.

## Gate 0 rationale

### Real product bug

The authoritative real-bug source is the owner-authored historical product
fix `a60756436095fb3b14aecbc9094dd88a8ab9ef16`, whose direct parent is
`15d5d51356b4808e5fb12782961a94d9985b2ae6`. The commit changes production
import logic and adds a regression fixture for the same strong-identity defect.

No separate Git note, associated pull request, issue, or production-incident
record was found. Admission therefore establishes a historical product-code
bug; it does **not** claim that an observed production incident was independently
recorded. This replaces the broader, unsupported reading of "recorded
production identity collision."

### Common baseline

The baseline and fixed roles use the exact commits above. The fix is the direct
child of the baseline, and the identical frozen test file is overlaid into both
roles. The effective production-code difference exercised by the pair is the
strong-identity guard in `import-logic.ts`.

### Credible oracle

Attempt 02 used the same byte-frozen oracle, dependency lock, image, command,
and injected environment for both roles. The expected strong-identity test
failed on the baseline while the other four focused tests passed; all five
passed on the fixed tree. The terminal record closed the pair as
`VERIFIED_FOR_GATE0_REVIEW` without performing admission itself.

Attempt 01 remains an immutable `ORACLE_DOES_NOT_DISCRIMINATE` result. Its
post-attempt causal analysis and the new attempt identity preserve that failed
history rather than repairing it in place.

## Claim ceiling and next boundary

C1 is now `ADMITTED_AT_GATE0`. This means only that a real historical
product-code bug, a common baseline, and a credible reconstructable oracle
exist.

This checkpoint does **not** establish:

- method sensitivity sufficient to justify Gate 1 cost;
- Gate 1 preregistration or authorization;
- A/B or counted Gate 3 execution;
- measured Skill effectiveness, effect size, prevalence, or generalization;
- countability, process integrity, or promotion evidence; or
- admission or execution of C2 or C3.

Any method-sensitivity assessment or Gate 1 proposal is a separate bounded
decision requiring fresh authority. C2 and C3 remain `NOT_VERIFIED` and
`NOT_ADMITTED`.
