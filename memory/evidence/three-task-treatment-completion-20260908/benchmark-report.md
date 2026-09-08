# Three-task Lite: preserved CONTROL + fresh TREATMENT

Scope: NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY.
CONTROL responses are the original single-run outputs. Only deterministic collection/oracle/regression was rerun under committed corrected harness bytes. CONTROL model was not invoked again.
TREATMENT uses the same frozen task/baseline/model/auth/timeout/environment settings with the frozen Skill packet. Context paths differ by design. Calls are not contemporaneous; no repeated-sample or generalized causal claim.

| Task | Status | CONTROL oracle / regression | TREATMENT oracle / regression | Quality C / T |
|---|---|---|---|---|
| easy_queue_range | COMPLETE | 12/12; tests=7, errors=7, failures=0 | 12/12; tests=9, errors=9, failures=0 | NOT_ASSESSABLE / NOT_ASSESSABLE |
| hard_dependency_cycle | COMPLETE | 14/14; tests=2, errors=0, failures=0 | 14/14; tests=3, errors=0, failures=0 | 8 / 8 |
| medium_interval_merge | COMPLETE | 13/13; tests=7, errors=0, failures=0 | 13/13; tests=7, errors=0, failures=0 | 8 / 8 |

## Evidence and interpretation

Regression test methods are actual unittest counts, not oracle cases or subTest iterations. Errors/NameError do not establish successful assertion execution and remain NOT_ASSESSABLE under the frozen rubric. Oracle correctness does not substitute for quality evidence.
Missing total means neither overall winner nor overall tie can be inferred. No source/test repair, material supplementation, scorer retry or post-unblinding score edit was performed.

## Model elapsed time (ms)

| Task | Original CONTROL | Fresh TREATMENT |
|---|---|---|
| easy_queue_range | 48969 | 43438 |
| hard_dependency_cycle | 36203 | 38766 |
| medium_interval_merge | 39234 | 39937 |

Detailed rubric evidence and mappings: per-task report.json; immutable scores: per-task scores-frozen.json. Raw completion evidence remains per-task, per-arm model/oracle/regression request/result/stdout/stderr.
Known runtime warnings are retained in runtime-warnings.json and never relabeled as no runtime issues.
Manual execution/data repair interventions: 0. Automatic adapter retries: 0. Owner authorization and normal tool approval are not classified as manual benchmark repairs.
Governance-cost observation: no new substantive governance friction observed in this execution slice; extra time not separately measured. Prior harness repair cost remains in its historical evidence.
No commit or push; STOP after aggregation. Real-model results alone do not establish generalized Skill efficacy, difficulty calibration, or average operating-cost reduction.

Observed result: no Treatment quality advantage established in these three tasks. Medium and Hard each score 8/8 versus 8/8. Easy has matching scores in three assessable dimensions but both regression ratings and totals are NOT_ASSESSABLE; no overall Easy tie or aggregate benchmark tie is claimed. Hard CONTROL also retained genuine cycle checks, so the observed results do not demonstrate a Treatment reduction in superficial fixes.

Current slice elapsed wall time: 199500 ms, including recollection, three Treatment calls and three fresh scorer calls; excludes historical CONTROL generation and earlier compatibility work. This is not total project time or proof of average savings.
