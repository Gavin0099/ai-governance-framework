# #17 Memory Authority Threshold Dry-Run Simulation - 2026-06-08

## Scope

Dry-run simulation of the current #17 advisory threshold proposal against
available active-window memory-authority samples.

This artifact documents candidate trigger behavior only. It does not enable
blocking, change hooks, change `memory_authority_guard`, change validators, or
change memory writer behavior.

## Candidate Rule Under Simulation

Source:
`artifacts/governance/copilot-memory-authority-advisory-threshold-proposal-2026-06-06.md`

Advisory warning would trigger when all of the following are true:

- `memory_write_attempted = yes`
- `canonical_writer_used = no` or absent
- session is in the post-Phase-1 active window

Operational proxy:

- `active_non_canonical_writer.count >= 1`

Blocking remains out of scope.

## Input Evidence

| Evidence source | Samples | Evidence maturity | Simulation use |
| --- | ---: | --- | --- |
| `copilot-memory-authority-trend-summary-2026-06-04.md` | 13 | pasted-response aggregate | advisory trend input only |
| `copilot-memory-authority-raw-verification-2026-06-04.md` | 12 checked | mixed raw verification | active-count and caveat input |
| #17 positive sample: `usb-if-hub-spec-reference` | 1 | reported post-push canonical-writer-success | repeatability input |
| #17 positive sample: `verilog-domain-contract` | 1 | reported post-push canonical-writer-success | repeatability input |

## Dry-Run Result Summary

| Bucket | Count | Would trigger advisory warning? | Notes |
| --- | ---: | --- | --- |
| clean_canonical pasted samples | 11 | no | all reported `canonical_writer_used=yes` and count 0 |
| no_memory_activity sample | 1 | no | no memory write attempted |
| unknown pasted sample | 1 | no | insufficient evidence; do not coerce unknown into violation |
| raw-verified gl_electron_tool clean samples | 9 | no | all located guards report count 0 |
| CFU verified no-memory sample | 1 | no | verified pre-memory no activity |
| CFU partially verified post-memory canonical samples | 2 | no | canonical evidence exists with pre/post caveat; not used as full clean proof |
| usb-if-hub-spec-reference canonical-writer-success | 1 | no | reported canonical writer markers and count 0 |
| verilog-domain-contract canonical-writer-success | 1 | no | reported canonical writer markers and count 0 |

Aggregate dry-run outcome:

```text
candidate_advisory_warnings = 0
candidate_blocking_events = 0
active_non_canonical_writer.count > 0 samples = 0
canonical_writer_positive_samples = 2
repo_diversity_for_positive_samples = 2
```

## Candidate Readiness Interpretation

Supported:

- The candidate advisory warning rule would not fire on the currently recorded
  active-window samples.
- There is positive canonical-writer-success evidence across two repos.
- Current samples support continued advisory-threshold discussion.

Not supported:

- Blocking threshold activation.
- Enforcement effectiveness.
- Copilot compliance as a general claim.
- Future violation risk being zero.
- Treating the unknown pasted sample as clean.
- Treating CFU partially verified rows as fully equivalent to raw-verified
  clean samples without the pre/post-memory caveat.

## Escalation Conditions Check

The 2026-06-06 proposal required all of the following before blocking-threshold
discussion could proceed:

| Condition | Current result | Met? |
| --- | --- | --- |
| At least one active violation with `evidence_source = raw_guard_json` | none observed | no |
| At least 5 raw-verified samples in a single repo showing consistent behavior | gl_electron_tool has 9 clean samples, but no violation behavior | partially, for clean behavior only |
| Separate reviewer-approved blocking gate contract | not present | no |
| `--fail-on-active-non-canonical-writer` tested in CI with false-positive/false-negative bounds | not present | no |

Conclusion:

```text
advisory_threshold_discussion = supported
blocking_threshold_ready = false
hook_or_guard_change_authorized = false
```

## Recommended Next Action

Keep #17 in advisory observe-only mode.

If more evidence is needed, collect one of the following before any enforcement
discussion:

- a raw-verified active violation sample, or
- additional cross-repo positive canonical-writer-success samples, or
- explicit reviewer request for a blocking-gate contract design slice.

## Claim Ceiling

CLAIMED:

- dry-run simulation of the existing #17 advisory threshold proposal against
  current active-window samples;
- candidate advisory warning count is 0 for the currently recorded samples;
- blocking threshold remains not ready.

NOT CLAIMED:

- guard behavior changed;
- hook behavior changed;
- validator behavior changed;
- blocking threshold enabled;
- Copilot compliance;
- memory semantic correctness;
- future violation risk;
- historical violation cleanup;
- CI false-positive or false-negative bounds.
