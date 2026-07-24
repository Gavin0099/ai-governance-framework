# Open-Source Validation & Governance-Control-Plane — CANDIDATE Inventory

Status: **strategy input, read-only. NOT adopted, NOT installed, NOT expanding
the framework.** Every tool below is a *candidate* pending a comparison on real
tasks (effect, false positives, false negatives, cost, maintenance). Nothing here
changes Gate 2, the frozen Bug Fix pilot, PLAN, or any enforcement. It is kept for
traceability so future decisions can cite a specific candidate, not re-derive it.

Provenance: distilled from an owner-supplied review thread on 2026-07-25. The
reviewer did not deep-read the repo, so any "framework currently has/lacks X"
claim in the source is inferred; the numbers (198 governance_tools, SARIF-
receivable, Semgrep-not-integrated) are this project's own, not independently
verified by the reviewer. Extends and partially corrects
[external-tooling-replaceability-inventory-20260724.md](external-tooling-replaceability-inventory-20260724.md).

## 0. Division of labor (the correct framing — adopt as principle, not as tooling)

```
Engineering Skill      → tells the agent HOW to change code
Open-Source Validators → mature tools CHECK the change (JSON/SARIF/JUnit out)
AI Governance          → pins versions, stores raw output, binds receipt↔commit,
                         separates new vs historical findings, bounds the claim
```

Governance must NOT re-implement a linter, SAST engine, dependency scanner, or
mutation engine. This matches program doc Section 2 and the prior inventory's
Section A.

## 1. Candidate validators by phase (NOT a roadmap; NOT installed)

- **Phase 1 (low-cost, mature, replayable):** pytest / Vitest; Ruff / ESLint;
  mypy / `tsc --noEmit`; ShellCheck; OSV-Scanner.
- **Phase 2 (security & boundary):** Semgrep CE; Gitleaks; oasdiff; pgTAP.
- **Phase 3 (test quality):** Hypothesis / fast-check; mutmut / Stryker
  (critical-path only, never whole-repo per commit).
- **Language packs (baseline only, real trigger is risk not language):**
  Python/Shell repos → pytest, Ruff, mypy, ShellCheck (+Semgrep, OSV, Gitleaks);
  TS/PostgreSQL repos → Vitest, ESLint, tsc, pgTAP (+Semgrep, OSV, Gitleaks,
  StrykerJS, fast-check; oasdiff if OpenAPI).
- **Gate 2 pilot pins (already frozen, experiment-specific, NOT latest):**
  ShellCheck 0.10.0, Ruff 0.6.9, mypy 1.11.2 — chosen to *measure* D−C, expected
  null on the pre-push semantic bug; a null Arm D is a valid result.

## 2. The sharpest insight: the gap is the CONTROL PLANE, not more scanners

The source correctly argues the missing layer is governance control, not
detection. Candidate control-plane standards (mature OSS, for LATER — see §5):

| Layer | Candidate standard | Purpose |
|---|---|---|
| Schema validation | CUE / JSON Schema | is the receipt structurally + semantically valid |
| Policy decision | OPA/Rego + Conftest | allow / warn / deny / human-review as policy-as-code |
| Provenance & integrity | in-toto + SLSA + Cosign (sigstore) / Witness | bind executor+steps+artifact, tamper-evidence, signature |
| Agent red-team / eval | Inspect AI; Promptfoo; garak | does the agent escape sandbox, read secrets, sabotage the verifier |
| Isolation | rootless container / gVisor / Firecracker | bound filesystem/network/secret/process |
| SBOM & VEX | Syft + OpenVEX/vexctl | inventory + a real waiver/exception lifecycle |
| Changed-line coverage | coverage.py + diff-cover | did the agent's new lines actually get exercised |

## 3. Three-state distinction (adopt as a principle now; cheap)

`execution_status ≠ finding_status ≠ governance_decision`. Exit 0 may mean
"ran" or "no findings" depending on the tool; a crash/timeout/kill is NOT
"clean". This is the same failure class this session hit repeatedly (a `git
bundle verify` that passed while `clone` was empty; `--out == --receipt-out`
returning success with a half set; `grep | head` masking a non-match). Minimum
states: execution {succeeded|failed|timeout|cancelled|partial|not_applicable};
finding {clean|findings_present|baseline_only|unknown}; decision
{allow|allow_with_warning|deny|human_review}.

## 4. Correction to the prior inventory (this project's own earlier analysis)

`external-tooling-replaceability-inventory-20260724.md` Section C listed
**receipt↔commit binding, evidence provenance, and claim policy** as "bespoke
governance semantics, not replaceable." **That was an over-classification.** Those
have mature OSS standards: provenance/tamper-evidence → in-toto + SLSA + Cosign;
claim/decision policy → OPA/Rego; receipt structure → CUE/JSON Schema. The
hand-rolled receipts built this session (`linked_commit` + sha256 + fail-closed
runner + completeness marker) are effectively a poor-man's in-toto attestation.
The correct statement is: these are **eventually replaceable by standards**, not
uniquely bespoke — but replacement is a post-pilot decision, not now.

## 5. Candidate experiment-design improvement: task strata

Instead of one averaged `D−C`, stratify by defect type so each measures where a
tool class plausibly helps:

| defect type | expected-valuable validator class |
|---|---|
| syntax / lint smell | Ruff, ESLint, ShellCheck |
| type contract | mypy, tsc |
| dependency vulnerability | OSV, Trivy |
| API compatibility | oasdiff, Pact, Schemathesis |
| parser / boundary | Hypothesis, fast-check, fuzzing |
| security pattern | Semgrep, ZAP |
| semantic / workflow | regression test, contract test, domain validator |
| test weakness | mutation testing |

This is a genuine methodology improvement (it fixes the pre-push pilot's
"D expected null → averaged score is misleading"). It is a **candidate for Gate 3
design only** and would require its own pre-registration + owner re-sign; it is
NOT applied to the frozen Gate 2 pilot.

## 6. What (if anything) is worth doing NEAR-TERM

Only two, and only as candidates — still not adopted here:
1. A **JSON Schema for the test-evidence receipt** (cheap; would have caught the
   missing `output_artifacts` and the half-set fail-open this session hit).
2. The **three-state distinction** in receipts (§3).

Everything else (OPA, in-toto, Inspect AI, sandboxes, SBOM/VEX, 30+ scanners) is
**post-pilot**. Adopting even the source's "P0" subset before one working pilot
would repeat the premature-expansion pattern the taxonomy review already warned
against.

## 7. Cannot claim

- That any of these tools is adopted, installed, or integrated.
- That Semgrep / OSV / oasdiff / Hypothesis / mutation testing / any control-plane
  standard has run against the three consumer repos.
- That open-source tools can fully replace the in-house governance_tools (needs a
  same-contract replacement experiment; this is a candidate map, not a result).
- That a green validator means the product is correct.
- That Gate 2 has any external-validator result, or that adopting this inventory
  advances Gate 2. The bottleneck remains running one blinded pilot, unchanged by
  this document.
