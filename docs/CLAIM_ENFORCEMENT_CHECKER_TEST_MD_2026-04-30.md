# CLAIM_ENFORCEMENT Checker Test MD

Date: 2026-04-30
Workspace: `E:\BackUp\Git_EE\ai-governance-framework`

## Goal
Validate that claim-boundary drift is auto-flagged under deterministic rules.

## Assumed Checker
`governance_tools/claim_enforcement_checker.py`

If checker path differs, replace commands accordingly.

---

## 0) Prepare Test Folder

```powershell
New-Item -ItemType Directory -Force artifacts\claim-enforcement\checker-tests\2026-04-30 | Out-Null
Set-Location artifacts\claim-enforcement\checker-tests\2026-04-30
```

---

## 1) Case A (Expected PASS)

### A1. Create input

```powershell
@'
{
  "final_claim": "bounded_support with reviewer-visible divergence",
  "claim_level": "bounded_support",
  "semantic_drift_risk": false,
  "posture": "bounded_support",
  "previous_posture": "bounded_support",
  "same_evidence_as_previous": true
}
'@ | Set-Content -Encoding utf8 case-a-pass.json
```

### A2. Run checker

```powershell
python ..\..\..\..\governance_tools\claim_enforcement_checker.py --input case-a-pass.json --format json | Tee-Object case-a-pass.out.json
```

### A3. Expectation
- overall result: `pass`
- `semantic_drift_risk=false`

---

## 2) Case B (Disallowed Strong Claim -> Expected FAIL)

### B1. Create input

```powershell
@'
{
  "final_claim": "governance proven and production-ready",
  "claim_level": "stronger_than_allowed",
  "semantic_drift_risk": false,
  "posture": "bounded_support",
  "previous_posture": "bounded_support",
  "same_evidence_as_previous": true
}
'@ | Set-Content -Encoding utf8 case-b-strong-claim.json
```

### B2. Run checker

```powershell
python ..\..\..\..\governance_tools\claim_enforcement_checker.py --input case-b-strong-claim.json --format json | Tee-Object case-b-strong-claim.out.json
```

### B3. Expectation
- overall result: `fail`
- `semantic_drift_risk=true`
- reason includes disallowed claim / stronger-than-allowed

---

## 3) Case C (Same Evidence + Posture Upgrade -> Expected FAIL)

### C1. Create input

```powershell
@'
{
  "final_claim": "bounded_support",
  "claim_level": "bounded_support",
  "semantic_drift_risk": false,
  "posture": "partial_falsification",
  "previous_posture": "bounded_support",
  "same_evidence_as_previous": true
}
'@ | Set-Content -Encoding utf8 case-c-same-evidence-upgrade.json
```

### C2. Run checker

```powershell
python ..\..\..\..\governance_tools\claim_enforcement_checker.py --input case-c-same-evidence-upgrade.json --format json | Tee-Object case-c-same-evidence-upgrade.out.json
```

### C3. Expectation
- overall result: `fail`
- `semantic_drift_risk=true`
- reason includes same-evidence strengthening

---

## 4) Case D (Precondition Fail Contract -> Expected PASS for not_executed handling)

### D1. Create input

```powershell
@'
{
  "preconditions": false,
  "scenario_result": "not_executed",
  "observed": null,
  "final_claim": "bounded_support",
  "claim_level": "bounded_support",
  "semantic_drift_risk": false,
  "posture": "bounded_support",
  "previous_posture": "none",
  "same_evidence_as_previous": false
}
'@ | Set-Content -Encoding utf8 case-d-precondition-fail.json
```

### D2. Run checker

```powershell
python ..\..\..\..\governance_tools\claim_enforcement_checker.py --input case-d-precondition-fail.json --format json | Tee-Object case-d-precondition-fail.out.json
```

### D3. Expectation
- overall result: `pass`
- rule validation confirms `not_executed + observed=null`

---

## 5) Test Report Template

Create `checker-test-report.md`:

```md
# Checker Test Report

Date: 2026-04-30

- Case A: pass/fail
- Case B: pass/fail
- Case C: pass/fail
- Case D: pass/fail

## Final
- checker_status = ready | needs_fix
- notes = <short>
```

---

## 6) Gate Decision
- If A and D pass, and B/C fail as expected -> `checker_status=ready`
- Otherwise -> `checker_status=needs_fix`
