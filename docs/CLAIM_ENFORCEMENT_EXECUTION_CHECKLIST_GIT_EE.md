# CLAIM_ENFORCEMENT Execution Checklist (Git_EE)

Base path: `E:\BackUp\Git_EE`

## Repo Set

### Pilot (Run First)
1. `USB-Hub-Firmware-Architecture-Contract`
2. `Kernel-Driver-Contract`
3. `verilog-domain-contract`

### Expansion (After Pilot)
4. `SpecAuthority`
5. `writing-contract`

---

## Standard Output Path (Per Repo)
Use this folder pattern inside each repo:

`artifacts/claim-enforcement/2026-04-30-pilot/<repo-name>/`

Required artifact files:
- `closeout-baseline.json`
- `closeout-drift-injection.json`
- `closeout-same-evidence-posture.json`
- `result-summary.md`

---

## Per-Repo Checklist Template

### [ ] Repo: `<repo-name>`
- [ ] Confirm `docs/CLAIM_BOUNDARY.md` exists
- [ ] Confirm `docs/CLAIM_ENFORCEMENT_MINIMAL_SPEC.md` exists
- [ ] Create output folder: `artifacts/claim-enforcement/2026-04-30-pilot/<repo-name>/`

#### A. Baseline Closeout
- [ ] Produce `closeout-baseline.json`
- [ ] Set `claim_level=bounded_support`
- [ ] Set `semantic_drift_risk=false`

#### B. Drift Injection (same evidence)
- [ ] Produce `closeout-drift-injection.json`
- [ ] Inject stronger wording (e.g. "proven" / "production-ready")
- [ ] Expect `claim_level=stronger_than_allowed`
- [ ] Expect `semantic_drift_risk=true`

#### C. Same-Evidence Posture Escalation
- [ ] Produce `closeout-same-evidence-posture.json`
- [ ] Set `same_evidence_as_previous=true`
- [ ] Attempt stronger posture than previous
- [ ] Expect `semantic_drift_risk=true`

#### D. Repo Result
- [ ] Write `result-summary.md`
- [ ] Mark repo `pass` only if A/B/C all match expected flags

---

## Filled Targets

### [ ] Repo: `USB-Hub-Firmware-Architecture-Contract`
- Path: `E:\BackUp\Git_EE\USB-Hub-Firmware-Architecture-Contract`
- Output: `E:\BackUp\Git_EE\USB-Hub-Firmware-Architecture-Contract\artifacts\claim-enforcement\2026-04-30-pilot\USB-Hub-Firmware-Architecture-Contract\`

### [ ] Repo: `Kernel-Driver-Contract`
- Path: `E:\BackUp\Git_EE\Kernel-Driver-Contract`
- Output: `E:\BackUp\Git_EE\Kernel-Driver-Contract\artifacts\claim-enforcement\2026-04-30-pilot\Kernel-Driver-Contract\`

### [ ] Repo: `verilog-domain-contract`
- Path: `E:\BackUp\Git_EE\verilog-domain-contract`
- Output: `E:\BackUp\Git_EE\verilog-domain-contract\artifacts\claim-enforcement\2026-04-30-pilot\verilog-domain-contract\`

### [ ] Repo: `SpecAuthority`
- Path: `E:\BackUp\Git_EE\SpecAuthority`
- Output: `E:\BackUp\Git_EE\SpecAuthority\artifacts\claim-enforcement\2026-04-30-pilot\SpecAuthority\`

### [ ] Repo: `writing-contract`
- Path: `E:\BackUp\Git_EE\writing-contract`
- Output: `E:\BackUp\Git_EE\writing-contract\artifacts\claim-enforcement\2026-04-30-pilot\writing-contract\`

---

## Pilot Exit Criteria
- 3 pilot repos all complete A/B/C checks
- 0 false negatives on strong-claim injection
- Any false positives documented in each `result-summary.md`

## Expansion Gate
Run expansion repos only after pilot exit criteria are met.
