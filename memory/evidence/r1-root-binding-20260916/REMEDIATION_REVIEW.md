# R1 two-P2 remediation and independent review

Date: 2026-09-16. Result: COMMIT_READY (technical readiness only; no commit performed).
Authority: owner explicitly bounded remediation to the two findings, four regression categories, original suite and exact remediation review.
Frozen reviewed subject: remediation-source-snapshot.json; base e5d819b47be58384eeda1a2d7672f9de16e1b63b, UNCOMMITTED.
Prior review and source-snapshot.json remain historical evidence, not overwritten.

## Disposition

| Question | Independent reviewer result |
|---|---|
| P2-1 closed? | YES. Unqualified writer rejects existing v1.1 before mutation. Envelope and current-session marker bytes preserved, including when v1.1 binding is malformed/missing. |
| P2-2 closed? | YES. Completion-only state rejected before mkdir/lock. Missing pointer stays absent; existing pointer remains unchanged. |
| Recheck under lock? | YES. Completion injected after preflight is rejected under lock; no envelope/marker, lock cleaned up. |
| v1.0 regression? | None observed. Legacy rewrite retains provider/started_at update and marker behavior. |
| Scope expansion? | NO. Only two guards and four regression categories (five parameterized cases). |

Code: runtime_hooks/core/_canonical_closeout.py:137; runtime_hooks/adapters/codex/session_start.py:62 (preflight) and :79 (recheck).
New tests: tests/test_session_root_binding.py:206, :218, :231, :253.

## Validation

Author command from this worktree root:

```text
python -B -m pytest tests/test_session_root_binding.py tests/test_codex_session_start.py tests/test_runtime_session_start.py tests/test_runtime_session_end.py tests/test_codex_closeout_identity.py tests/test_agent_closeout_receipt.py -q -p no:cacheprovider --junitxml=memory/evidence/r1-root-binding-20260916/remediation-tests.xml
```

Result: 122 passed in 60.82s. Original 117 plus five new cases. Artifact: remediation-tests.xml.

Independent reviewer /root/r1_independent_review returned APPROVED on the exact remediation hashes. It separately executed six disposable Git repository cases via python -B -, including malformed v1.1, legacy rewrite, absent/existing pointer and injected completion race. Six cases passed. It did not rerun the author's 122 tests. This is independent AI review, not human/external certification.

git diff --check passed (line-ending advisories only).

## Boundaries

No commit, push, PR, merge, consumer activation, R2, preparation helper or session closeout performed. Existing valid consumed-envelope resume/marker-refresh behavior is unchanged. Workspace candidate remains uncommitted; unrelated original workspace state is explicitly excluded.

Merging R1 framework code does NOT authorize installing or enabling the v1.1-producing SessionStart path in any consumer whose bound framework reader compatibility has not been verified. Mixed-version deployment and Memory E2E remain unqualified.

## Machine response envelope

```json
{
  "mode": "compact",
  "mode_source": "milestone_completed",
  "task_authority": "Owner authorized two-P2 remediation, four regression categories, scoped suite and independent remediation review",
  "scope": "R1 two-P2 remediation only",
  "done": "Local remediation and independent review complete; uncommitted candidate technically COMMIT_READY",
  "claim_ceiling": "122 author tests and six independent disposable cases on exact uncommitted source hashes",
  "not_claimed": ["committed scope DONE", "delivery", "PR", "merge", "consumer activation", "R2", "mixed-version deployment qualification", "Memory E2E"],
  "evidence_refs": ["remediation-source-snapshot.json", "remediation-tests.xml", "REMEDIATION_REVIEW.md", "INDEPENDENT_REVIEW.md"],
  "risk": "Candidate remains uncommitted; deployment reader compatibility requires separate verification",
  "next_action": "Scoped commit preflight and explicit staging allowlist when commit is authorized"
}
```
