# CLAIM_ENFORCEMENT Pilot Test Plan

## Recommended Repo Count
- Pilot phase: 3 repos
- Expansion phase: +2 repos after pilot review

Reason:
- 3 repos is enough to expose common semantic-drift patterns without making流程過重。

## Suggested Pilot Repos
1. `examples/usb-hub-contract` (已知基準，可當對照)
2. `examples/todo-app-demo` (一般應用場景)
3. `examples/cpp-userspace-contract` (規則密度較高場景)

## Test Objective
Verify that claim wording cannot silently drift upward under the same evidence.

## Required Output Files Per Repo
- `docs/CLAIM_BOUNDARY.md` (already defined)
- `docs/CLAIM_ENFORCEMENT_MINIMAL_SPEC.md` (already defined)
- One reviewer closeout JSON including required fields:
  - `final_claim`
  - `claim_level`
  - `semantic_drift_risk`
  - `posture`
  - `previous_posture`
  - `same_evidence_as_previous`

## Per-Repo Test Checklist

### A. Baseline Closeout
- Produce closeout with conservative wording:
  - `claim_level=bounded_support`
  - `semantic_drift_risk=false`

### B. Drift Injection (Controlled)
- Keep evidence unchanged.
- Rewrite claim wording to stronger phrasing (e.g., "proven", "production-ready").
- Expected result:
  - `claim_level=stronger_than_allowed`
  - `semantic_drift_risk=true`

### C. Same-Evidence Posture Escalation Check
- Keep `same_evidence_as_previous=true`.
- Try upgrading `posture` (e.g., from `bounded_support` to stronger interpretation).
- Expected result:
  - `semantic_drift_risk=true`

## Pass Criteria (Per Repo)
- System flags drift in both B and C.
- Conservative baseline in A remains unflagged.

## Pilot Success Criteria (Overall)
- 3/3 repos complete A/B/C checks.
- 0 false negatives for obvious strong-claim injections.
- Any false positives are documented for wording refinement.

## Report Template

```yaml
repo: <repo_name>
baseline:
  claim_level: bounded_support
  semantic_drift_risk: false

drift_injection:
  claim_phrase_used: <text>
  claim_level: stronger_than_allowed
  semantic_drift_risk: true

same_evidence_posture_check:
  previous_posture: <value>
  current_posture: <value>
  same_evidence_as_previous: true
  semantic_drift_risk: true

result: pass | fail
notes: <short>
```

## Next Step After Pilot
If pilot passes, add 2 more repos (`nextjs-byok-contract`, `chaos-demo`) and repeat with identical rules.
