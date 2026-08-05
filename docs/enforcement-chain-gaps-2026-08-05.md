# Enforcement chain gaps — framework-side remediation (2026-08-05)

## What this change is about

A consumer repo was described as having "fully adopted AI governance" while a
guard that could detect the problem produced no effect. The detector was not
broken. What was missing sat between the detector and any consequence.

Six things were being conflated into one word, "adopted":

1. the tool exists in the checkout
2. something wires it into a runtime path
3. it actually runs, leaving evidence
4. it provably examined the scope it claims to cover
5. its findings reach a verdict
6. its findings can make that verdict blocking

A repo at (1) or (2) detects nothing in practice. "Files copied, contract
present, tool runs by hand" is evidence for (1) and (2) only, and was being
reported as if it covered all six.

This change addresses the four framework-side gaps. Consumer-side work
(single provable framework execution source, submodule re-pin, a domain
validator that understands its own tool output) is not in scope here.

## 1. Evidence roots are declared, not hardcoded

**Was:** provenance checks matched `artifacts/...` and nothing else. A repo
storing receipts anywhere else produced
`test_evidence_success_claim_without_artifact` for every entry — the same
finding as a repo that cited no evidence at all. The two are not remotely the
same problem, and the finding stream could not distinguish them.

**Now:** `contract.yaml` may declare

```yaml
evidence_roots:
  - artifacts
  - Tools/DriverTests/Evidence
  - memory/governance_onboarding
```

Consumer declarations are **additive**, not a replacement. An earlier draft
made them replace the default; that was wrong and provably so — the framework
writes its own runtime closeouts, verdicts and receipts under `artifacts/`, so
a contract declaring only `Tools/DriverTests/Evidence` stopped the framework
from recognising its own artifacts and produced spurious mixed-scope findings.
`artifacts` is framework-owned and cannot be removed by a contract.

An explicitly empty `evidence_roots:` is a misconfiguration, not a default: it
reports source `contract_declared_empty` with a warning rather than silently
resembling an absent key.

Widening the accepted surface without tightening what counts would trade one
bad signal for another, so a cited path is accepted only when it is
repo-relative, free of parent traversal, resolves inside the project root
(symlinks followed, so a linked directory cannot escape), sits under a
declared root, and is an existing regular file.

Findings now split into four buckets — carried in `reason` and in a new
`provenance_subcode` field:

| bucket (`provenance_subcode`) | meaning |
|---|---|
| `no_parsable_artifact_reference` | no reference the tool could parse — *not* proof the author cited nothing |
| `outside_declared_roots` | an existing output file is cited from an undeclared location — a contract gap |
| `artifact_not_found` | declared root, absent file |
| `path_unsafe` | absolute, traversing, or escaping the repository |

The first bucket is deliberately *not* named "success claim without artifact".
Path detection is heuristic: quoted paths, unfamiliar formats and undeclared
extensions can all be missed, so the count is "no reference this tool could
parse", never "the author cited nothing". The underlying `reason` string keeps
its legacy value because `memory_authority_baseline` builds bucket identity
from `reason` — renaming it would invalidate every existing baseline and force
a rebuild, which is exactly how historical debt gets washed away.

Detection covers Windows domain evidence (`.etl`, `.evtx`, `.cat`, `.inf`,
`.dmp`) because driver work is a first-class consumer case, accepts
extension-less files that actually exist, reads quoted paths containing spaces,
and honours `evidence_file_suffixes:` for formats the framework has never heard
of. Root matching follows the filesystem's case rule.

The `outside_declared_roots` bucket is deliberately narrow. A `test_evidence`
line names both what was run and what it produced — `PASS: pytest
tests/test_foo.py` cites a test target, not a receipt. Counting that as
misplaced evidence would relabel unsupported claims as mere contract gaps,
which is the same failure as before with the sign flipped. So the bucket
requires the cited path to be an existing file with an output-shaped extension
(`.json`, `.ndjson`, `.log`, `.xml`, …), judged on extension rather than naming
convention: a `.py` file is not a receipt whatever it is called.

Measured on this repository, the split is 447 / 6 / 4 across
`no_parsable_artifact_reference` / `artifact_not_found` /
`outside_declared_roots` out of 457 findings — the same total as before,
reclassified rather than reduced. Before the narrowing it read 75 / 6 / 376,
which would have led triage badly astray. The 447 is a parser result, not a
census of dishonest claims; treat it as a queue to inspect, not a number to
quote.

`run_guard` reports the roots in effect under `evidence_root_policy`, including
whether they came from the contract or the framework default. Triaging an
existing backlog of provenance findings starts here: group by
`provenance_subcode` before concluding anything about any of them.

A contract discovered *above* the project root is ignored with a warning.
Discovery walks upward, and a parent repo's evidence roots do not describe a
nested one.

**Code:** `governance_tools/evidence_roots.py`; wired into
`memory_authority_guard` and `memory_provenance`.

## 2. Adoption state is machine-readable

**Was:** nothing reported the five states separately, so nothing could
contradict a claim of full adoption.

**Now:** `governance_tools/guard_enforcement_census.py` reports, per registered
surface, the highest level with evidence, and names the first missing link.

```
python -m governance_tools.guard_enforcement_census --project-root .
```

Surfaces are declared in `governance/guard_surface_registry.json`. Adding a
file to `governance_tools/` does not register it; registration is deliberate.

Four properties matter more than the output format:

- **The ladder does not skip.** A surface whose codes are policy-enabled but
  which nothing ever invokes is reported at `configured`, not `blocking`. The
  raw check stays visible as true, but the level does not jump the gap —
  otherwise a dead guard reads as an active one.
- **Stale evidence is not invocation.** Evidence older than the freshness
  window (default 30 days) proves it ran once, not that it runs now.
- **Executing is not examining.** `covered` is its own rung: a guard pointed at
  a directory that does not exist runs perfectly and sees nothing. A surface
  declares `full_scan` (coverage follows from invocation plus the root
  existing) or `changed_paths` (coverage requires the run to have recorded the
  scope it saw). Most surfaces today stop at `invoked` with
  `examined_scope_not_recorded` — which is the honest state, not a bug.
- **There is no aggregate verdict.** The result has no `ok`, no `adopted`, no
  `compliant` field. Adoption is not a state this tool can certify, and a
  report with such a field would be quoted as if it could.

Reported alongside the ladder, not as a rung: `version_alignment`, comparing
`governance/framework.lock.json` with the framework actually present. A drifted
checkout can be fully wired and still enforce an older contract, so drift caps
what the census may be quoted for rather than lowering a level. Direction is
reported (`behind_pin` / `ahead_of_pin` / `diverged`), which is the machine
answer to "the submodule is N commits behind" — provable rather than inferred
from a commit count. A pin that cannot be verified reports `unknown`, never
`aligned`.

Run against this repository, the census immediately shows
`daily_memory_gate` at `present` — the file exists and nothing references it —
and `claim_enforcement_checker` at `invoked`, running without its findings
reaching a verdict.

## 3. Strong claims bind to a registered validator's receipt

The framework must not learn what `pnputil` output means. That is domain
knowledge and belongs in a domain validator. But "the framework does not judge
domain semantics" was doing more work than it should: it left no one checking
whether a PASS came from *any* semantic judgement at all.

The split:

- **Domain validator:** parse the tool output, decide what actually happened,
  emit a receipt.
- **Framework:** the claim kind is registered, the receipt *names* the
  registered validator, the validator exists, the receipt is anchored to this
  session and commit, its cited evidence resolves under declared roots, and its
  verdict rests on more than a process exit code.

**Known gap, stated rather than papered over.** Every field checked is
self-reported by the receipt, so an agent that writes the JSON by hand with
correct values passes. `bound` therefore means *schema-and-anchor consistent
with a registered producer*, not *validated by a registered validator*, and the
result carries that in `binding_strength` and `not_claimed`. Closing it needs an
invocation id issued by a canonical runner, a validator code digest, and a
create-once ledger the producer cannot write to. A test pins the exposure so it
cannot be silently assumed away.

That last rule is the pnputil case stated without any domain knowledge: a
receipt whose `verdict_basis` is only `exit code 0`, `rc 0`, `process
succeeded` or similar cannot support a strong claim. Mentioning the exit code
alongside a real basis is fine; resting on it alone is not.

Unbound strong claims are downgraded to `observed_unverified`. Whether an
unbound claim also blocks is a policy decision this module does not make.
Observed-strength claims report `not_required`, not `bound`: retaining an
observation-grade claim does not imply any producer or validator binding.

**Code:** `governance_tools/claim_validator_binding.py`, registry
`governance/claim_binding_registry.json` (schema `claim_binding_registry.v0.1`),
receipt schema `domain_validator_receipt.v0.1`.

A missing registry means no claim kind is registered, so every strong claim is
unbound. It never means everything is fine.

## 4. Advisory → blocking has criteria, and "N days with zero findings" is not one

Zero findings is ambiguous between a clean repo, a guard nobody ran, a scope
that matches nothing, a broken matcher, and a baseline that swallowed
everything. Promoting on silence promotes whichever of those is actually true.
The rejection is recorded in the criteria file itself so it cannot be
reintroduced as an obvious idea.

`governance/blocking_graduation_criteria.json` requires instead:

| criterion | kind |
|---|---|
| guard at census level `invoked` or higher | machine |
| ran in ≥90% of sessions closed in the observation window (≥10 sessions) | machine |
| no active in-window `non_canonical_writer` violations — historical debt stays advisory and is deliberately not counted | machine |
| known-positive and known-negative fixtures both judged correctly | attestation |
| false-positive/false-negative sample reviewed and dispositioned | attestation |
| bypass mutation run confirms the check fails when the property breaks | attestation |
| a deliberately introduced in-window finding was observed actually blocking | attestation |
| the frozen baseline cannot suppress an in-window finding | machine |
| a documented break-glass path exists and the policy is writable | machine |
| owner approved this enforcement profile | attestation, human only |

`governance_tools/blocking_graduation_check.py` evaluates these into `met`,
`not_met`, or `unevaluable`. `unevaluable` is a distinct outcome on purpose: an
observation window with too few sessions answers nothing, and must read as
neither pass nor fail. Unevaluable blocks a proposal exactly as failing does,
because the question stays open.

Attestations must name a signer in `owner_registry`, cite an authority document matching
`authority_ref_patterns` (any existing file would otherwise do — `README.md` is
not an authority document), carry the sha256 of the criteria file so an
approval is bound to what it approved, record a true result, and be within the
age window. Those checks validate the declaration, not the signer: repository
JSON is inside the agent's write authority, so every structurally valid
attestation remains `unevaluable` until identity provenance is verified by a
mechanism outside that authority. An attestation that names an AI identity is
rejected outright.

Weakening the criteria after signing invalidates the signature, because the
recorded digest no longer matches.

The observation window cannot be reset by rebuilding the baseline: a baseline
whose mtime falls inside the window makes `active_violations_clear`
`unevaluable`, since re-freezing current debt can zero active findings without
anything being fixed. `baseline_non_interference` takes the active-window
cutoff from the guard rather than from the baseline file, so a baseline that
simply omits the field cannot pass vacuously.

The tool cannot enable anything. Graduation stays a human edit to
`governance/memory_blocking_policy.json`.

## What this does not fix

- The census reports wiring, not correctness. A surface at `blocking` may still
  have wrong findings or a reachable bypass.
- `bound` on a claim does not prove the validator ever ran — see the known gap
  in section 3. It is the largest remaining hole in this work.
- Evidence-path detection remains heuristic. It is narrower and better named
  than before, but "no parsable reference" is a parser outcome, not a finding
  of fact about the author.
- Only the evidence-root resolver is wired into an existing execution chain.
  The census, claim binding and graduation check are readiness artifacts that
  no canonical caller invokes; `claim_validator_binding` is deliberately
  unwired. Wiring them into the closeout
  path changes when sessions fail, which is an owner decision, not a side
  effect of adding the tools. The census reports them as `present` until then —
  which is the honest state.
- Nothing here touches the consumer side: framework execution source
  uniqueness, submodule currency, and the domain validator that reads
  `pnputil` output remain open.
